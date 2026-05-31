"""Start an RQ worker for background jobs.

Run as: python -m app.tasks.worker
"""
import os
import logging

from rq import Worker, Queue
from redis import Redis

logging.basicConfig(level=logging.INFO)


def main() -> None:
    # read redis url from app settings
    from app import config

    redis = Redis.from_url(config.settings.redis_url)
    q = Queue("default", connection=redis)
    worker = Worker([q], connection=redis)
    worker.work()


if __name__ == "__main__":
    main()
import os
import logging
from redis import Redis
from rq import Worker, Queue, Connection

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
