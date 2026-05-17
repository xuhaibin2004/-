import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.redis import redis_client, STATUS_CHANNEL

router = APIRouter()
logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)

    def disconnect(self, task_id: str, websocket: WebSocket):
        if task_id in self.active_connections:
            self.active_connections[task_id].remove(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]

    async def send_to_task(self, task_id: str, message: dict):
        if task_id in self.active_connections:
            for ws in self.active_connections[task_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass


manager = ConnectionManager()


@router.websocket("/tasks/{task_id}")
async def websocket_task_status(websocket: WebSocket, task_id: str):
    await manager.connect(task_id, websocket)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(STATUS_CHANNEL)
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    if data.get("task_id") == task_id:
                        await websocket.send_json(data)
                except (json.JSONDecodeError, KeyError):
                    pass
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        manager.disconnect(task_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {e}")
        manager.disconnect(task_id, websocket)
    finally:
        await pubsub.unsubscribe(STATUS_CHANNEL)
        await pubsub.close()
