import asyncio
import json
import logging
import uuid

from app.core.redis import redis_client, STREAM_KEY, STREAM_GROUP
from app.services.task_scheduler import task_scheduler

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAYS = [5, 30, 120]


async def process_task(message: dict):
    task_id_str = message.get("task_id")
    if not task_id_str:
        logger.error("No task_id in message")
        return
    task_id = uuid.UUID(task_id_str)
    retry_count = int(message.get("retry_count", "0"))
    try:
        await task_scheduler.run_task(task_id)
    except Exception as e:
        logger.error(f"Task {task_id} processing failed (attempt {retry_count + 1}): {e}")
        if retry_count < MAX_RETRIES:
            delay = RETRY_DELAYS[min(retry_count, len(RETRY_DELAYS) - 1)]
            await asyncio.sleep(delay)
            await redis_client.xadd(
                STREAM_KEY,
                {
                    "task_id": task_id_str,
                    "retry_count": str(retry_count + 1),
                },
            )
            logger.info(f"Task {task_id} requeued (attempt {retry_count + 2})")
        else:
            logger.error(f"Task {task_id} exceeded max retries")


async def run_worker():
    logger.info("Starting task worker...")
    consumer_name = f"worker-{uuid.uuid4().hex[:8]}"
    while True:
        try:
            messages = await redis_client.xreadgroup(
                STREAM_GROUP,
                consumer_name,
                {STREAM_KEY: ">"},
                count=1,
                block=5000,
            )
            if messages:
                for stream, msg_list in messages:
                    for msg_id, msg_data in msg_list:
                        try:
                            await process_task(msg_data)
                            await redis_client.xack(STREAM_KEY, STREAM_GROUP, msg_id)
                        except Exception as e:
                            logger.error(f"Error processing message {msg_id}: {e}")
        except Exception as e:
            logger.error(f"Worker error: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())
