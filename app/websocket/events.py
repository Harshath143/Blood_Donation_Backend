import structlog

logger = structlog.get_logger()

async def handle_websocket_event(user_id: str, data: dict, ws_manager):
    """
    Dispatcher for inbound WebSocket messages.
    """
    event_type = data.get("event")
    logger.info("websocket_inbound_event", user_id=user_id, event=event_type)

    if event_type == "ping":
        await ws_manager.send_to_user(user_id, {"event": "pong"})
    else:
        logger.warning("websocket_unknown_event", user_id=user_id, event=event_type)
