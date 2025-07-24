from typing import Dict, List
from fastapi import WebSocket # type: ignore

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, group: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(group, []).append(websocket)

    def disconnect(self, group: str, websocket: WebSocket):
        if group in self.active_connections:
            self.active_connections[group].remove(websocket)
            if not self.active_connections[group]:
                del self.active_connections[group]

    async def send_to_group(self, group: str, message: str):
        for conn in self.active_connections.get(group, []):
            await conn.send_json({"message": message})


manager = WebSocketManager()
