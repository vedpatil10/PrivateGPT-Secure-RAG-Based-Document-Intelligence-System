"""
Run the ingestion worker as a standalone long-lived process.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.logging_config import setup_logging
from config.settings import get_settings
from models.database import close_db, init_db
from services.ingestion.pipeline import get_ingestion_pipeline


async def main():
    settings = get_settings()
    logger = setup_logging("DEBUG" if settings.debug else "INFO")
    pipeline = get_ingestion_pipeline()

    logger.info("Starting standalone ingestion worker")
    await init_db()
    await pipeline.start_background_worker()

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Stopping standalone ingestion worker")
    finally:
        await pipeline.stop_background_worker()
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
