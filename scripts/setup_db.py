"""
Database initialization and admin user creation.
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import init_db
from services.auth_service import AuthService
from models.database import async_session_factory
from config.logging_config import setup_logging


async def main():
    logger = setup_logging("INFO")
    logger.info("Initializing database...")

    await init_db()
    logger.info("✅ Database tables created")

    # Create default admin user
    try:
        async with async_session_factory() as db:
            result = await AuthService.register(
                org_name="Default Organization",
                email="admin@privategpt.local",
                password="admin123!",
                full_name="Admin User",
                db=db,
            )
            logger.info(f"✅ Admin user created: admin@privategpt.local (password: admin123!)")
    except ValueError as e:
        logger.info(f"Admin user already exists: {e}")

    logger.info("✅ Setup complete!")


if __name__ == "__main__":
    asyncio.run(main())
