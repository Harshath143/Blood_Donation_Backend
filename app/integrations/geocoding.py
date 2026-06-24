import json
import httpx
import structlog
from redis.asyncio import Redis
from app.config import get_settings

settings = get_settings()
logger = structlog.get_logger()

class GeocodingService:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.client = httpx.AsyncClient(
            headers={"User-Agent": f"{settings.APP_NAME}/{settings.APP_VERSION} (support@lifedrop.in)"},
            timeout=10.0
        )

    async def geocode(self, address: str, city: str, state: str) -> tuple[float | None, float | None]:
        """
        Geocodes address details into latitude and longitude.
        Uses Redis to cache results and avoid excessive external API hits.
        """
        query = f"{address}, {city}, {state}".strip().lower()
        cache_key = f"geocode:{query}"
        
        # Check cache
        cached = await self.redis.get(cache_key)
        if cached:
            try:
                coords = json.loads(cached)
                logger.info("geocoding_cache_hit", query=query, lat=coords["lat"], lon=coords["lon"])
                return coords["lat"], coords["lon"]
            except Exception:
                pass
                
        # Cache miss, call Nominatim
        logger.info("geocoding_cache_miss", query=query)
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": query,
            "format": "json",
            "limit": 1
        }
        
        try:
            response = await self.client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    
                    # Store in cache (7 days TTL)
                    await self.redis.set(
                        cache_key,
                        json.dumps({"lat": lat, "lon": lon}),
                        ex=7 * 24 * 3600
                    )
                    return lat, lon
                else:
                    logger.warning("geocoding_no_results", query=query)
            else:
                logger.error("geocoding_api_error", status_code=response.status_code, body=response.text)
        except Exception as e:
            logger.error("geocoding_failed", error=str(e))
            
        return None, None

    async def close(self):
        await self.client.aclose()
