"""
Database initialization and admin user creation.
"""

import asyncio
import os
import sys

from alembic import command
from alembic.config import Config

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.logging_config import setup_logging
from config.settings import get_settings
from models.database import async_session_factory
from services.auth_service import AuthService


def run_migrations():
    """Apply Alembic migrations before seeding data."""
    repo_root = os.path.dirname(os.path.dirname(__file__))
    alembic_cfg = Config(os.path.join(repo_root, "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", get_settings().sync_database_url)
    command.upgrade(alembic_cfg, "head")


async def main():
    logger = setup_logging("INFO")
    logger.info("Initializing database")

    run_migrations()
    logger.info("Database migrations applied")

    try:
        async with async_session_factory() as db:
            await AuthService.register(
                org_name="Default Organization",
                email="admin@privategpt.local",
                password="admin123!",
                full_name="Admin User",
                db=db,
            )
            logger.info("Admin user created: admin@privategpt.local (password: admin123!)")
    except ValueError as e:
        logger.info(f"Admin user already exists: {e}")

    logger.info("Setup complete")


if __name__ == "__main__":
    asyncio.run(main())
