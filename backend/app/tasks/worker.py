"""Start an RQ worker for background jobs.

Run as: python -m app.tasks.worker
"""

import logging

from redis import Redis
from rq import Connection, Queue, Worker

from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agentforge.rqworker")

listen = ["default"]

redis_conn = Redis.from_url(settings.redis_url)

if __name__ == "__main__":
    with Connection(redis_conn):
        worker = Worker(list(map(Queue, listen)))
        logger.info("Starting RQ worker, listening queues: %s", listen)
        worker.work()
