from fastapi import WebSocket
import structlog

logger = structlog.get_logger()

class ConnectionManager:
    def __init__(self):
        # Maps user_id -> list of active WebSockets
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info("websocket_connected", user_id=user_id, total_connections=len(self.active_connections[user_id]))

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
                logger.info("websocket_disconnected", user_id=user_id)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_to_user(self, user_id: str, message: dict):
        """Send message directly to all active connections of a specific user."""
        if user_id in self.active_connections:
            connections = self.active_connections[user_id]
            logger.info("websocket_sending_to_user", user_id=user_id, message=message, connections_count=len(connections))
            for websocket in list(connections):
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error("websocket_send_error", user_id=user_id, error=str(e))
                    self.disconnect(user_id, websocket)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        logger.info("websocket_broadcasting", message=message)
        for user_id, connections in list(self.active_connections.items()):
            for websocket in list(connections):
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error("websocket_broadcast_error", user_id=user_id, error=str(e))
                    self.disconnect(user_id, websocket)

# Global singleton
ws_manager = ConnectionManager()
