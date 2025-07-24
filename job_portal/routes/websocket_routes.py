from fastapi import WebSocket, APIRouter # type: ignore
from job_portal.core.ws_manager import manager

router = APIRouter()

@router.websocket("/ws/{group}")
async def websocket_endpoint(websocket: WebSocket, group: str):
    await manager.connect(group, websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        manager.disconnect(group, websocket)
