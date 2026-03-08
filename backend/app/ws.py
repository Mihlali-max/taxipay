from collections import defaultdict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections = defaultdict(list)

    async def connect(self, trip_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[trip_id].append(websocket)

    def disconnect(self, trip_id: str, websocket: WebSocket):
        if trip_id in self.active_connections and websocket in self.active_connections[trip_id]:
            self.active_connections[trip_id].remove(websocket)

    async def broadcast(self, trip_id: str, message: dict):
        dead = []
        for connection in self.active_connections.get(trip_id, []):
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)

        for connection in dead:
            self.disconnect(trip_id, connection)

manager = ConnectionManager()
