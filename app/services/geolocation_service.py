from redis.asyncio import Redis
from app.integrations.geocoding import GeocodingService

class GeolocationService:
    def __init__(self, redis: Redis):
        self.geocoder = GeocodingService(redis)

    async def get_coordinates(self, address: str, city: str, state: str) -> tuple[float | None, float | None]:
        """Lookup latitude and longitude using the geocoding integration."""
        return await self.geocoder.geocode(address, city, state)
