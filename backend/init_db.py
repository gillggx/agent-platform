#!/usr/bin/env python3
"""
Database initialization script

This script:
1. Creates all database tables
2. Seeds default system agents and workflow templates
3. Can be run multiple times safely
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.db.base import Base
from app.data.seed_data import seed_all_defaults
from app.db.base import AsyncSessionLocal


async def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    
    engine = create_async_engine(settings.database_url, echo=True)
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()
    print("✓ Database tables created")


async def seed_defaults():
    """Seed default system data"""
    print("Seeding default system data...")
    
    async with AsyncSessionLocal() as db:
        await seed_all_defaults(db)
    
    print("✓ Default system data seeded")


async def main():
    """Main initialization function"""
    print("🚀 Initializing Multi-Agent Collaboration Platform database...")
    
    try:
        # Check database connection
        print("Testing database connection...")
        engine = create_async_engine(settings.database_url)
        async with engine.begin() as conn:
            result = await conn.execute("SELECT 1")
            result.fetchone()
        await engine.dispose()
        print("✓ Database connection successful")
        
        # Create tables
        await create_tables()
        
        # Seed default data
        await seed_defaults()
        
        print("\n🎉 Database initialization completed successfully!")
        print("\nYou can now start the application:")
        print("  Backend:  uvicorn app.main:app --host 0.0.0.0 --port 8000")
        print("  Frontend: npm run dev")
        print("  Docker:   docker-compose up")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())