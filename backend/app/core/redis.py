import redis.asyncio as redis

from app.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

STREAM_KEY = "task_stream"
STREAM_GROUP = "task_workers"
STATUS_CHANNEL = "task_status"


async def init_redis():
    global redis_client
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await redis_client.xgroup_create(STREAM_KEY, STREAM_GROUP, id="0", mkstream=True)
    except Exception:
        pass


async def close_redis():
    await redis_client.close()


async def publish_task_status(task_id: str, status: str, data: dict = None):
    message = {"task_id": task_id, "status": status}
    if data:
        message.update({k: str(v) for k, v in data.items()})
    await redis_client.publish(STATUS_CHANNEL, str(message))
