from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from redis.asyncio import Redis
import structlog
from uuid import UUID

from app.websocket.manager import ws_manager
from app.websocket.events import handle_websocket_event
from app.core.security import verify_token
from app.dependencies import get_redis

logger = structlog.get_logger()
router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    redis: Redis = Depends(get_redis)
):
    """
    WebSocket gateway connection.
    Secured by verifying the JWT token passed as a query parameter.
    """
    user_id = None
    try:
        payload = await verify_token(token, redis)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token payload")
            return
    except Exception as e:
        logger.error("websocket_auth_failed", error=str(e))
        # 4001 is a custom policy violation close code
        try:
            await websocket.close(code=4001, reason="Authentication failed")
        except Exception:
            pass
        return

    # Accept connection and register with connection manager
    await ws_manager.connect(user_id, websocket)
    
    try:
        while True:
            # We expect clients to communicate using JSON format
            data = await websocket.receive_json()
            await handle_websocket_event(user_id, data, ws_manager)
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id, websocket)
    except Exception as e:
        logger.error("websocket_error", user_id=user_id, error=str(e))
        ws_manager.disconnect(user_id, websocket)
