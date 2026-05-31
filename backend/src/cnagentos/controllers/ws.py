"""WebSocket endpoint for real-time chat (Phase 6+).

Phase 5 establishes the WebSocket protocol foundation:
  - Cookie-based session authentication on upgrade
  - JSON message framing
  - Connection lifecycle management

Full message routing and chat logic is implemented in Phase 6.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import async_sessionmaker

from cnagentos.config import get_settings
from cnagentos.services.auth import load_context

router = APIRouter()


@router.websocket("/api/v1/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket echo endpoint with session authentication.

    Protocol:
      - Client connects with session cookie (``cnagentos_session`` or
        ``__Host-cnagentos_session`` in production).
      - Server validates the session and sends a ``connected`` event.
      - Client sends JSON frames; server echoes them back.
      - Heartbeat: server pings every 30 s; connection closed if no
        response within 10 s (TBD in Phase 6).

    Message frame format:
        {"type": "<event_type>", "payload": {...}, "id": "<optional_uuid>"}
    """
    await websocket.accept()

    settings = get_settings()
    session_token = websocket.cookies.get(settings.session_cookie_name)

    if not session_token:
        await websocket.send_json({"type": "error", "payload": {"code": "UNAUTHENTICATED"}})
        await websocket.close(code=4001)
        return

    sessionmaker = async_sessionmaker(websocket.app.state.engine, expire_on_commit=False)
    try:
        async with sessionmaker() as db_session:
            context = await load_context(db_session, settings, session_token)
    except Exception:
        await websocket.send_json({"type": "error", "payload": {"code": "UNAUTHENTICATED"}})
        await websocket.close(code=4001)
        return

    await websocket.send_json({
        "type": "connected",
        "payload": {"user_id": context.user.id, "username": context.user.username},
    })

    try:
        while True:
            data = await websocket.receive_json()
            # Phase 5: echo only. Real message routing in Phase 6.
            await websocket.send_json({
                "type": "echo",
                "payload": data,
                "user_id": context.user.id,
            })
    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
