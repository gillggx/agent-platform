"""
Agent Worker - Processes long-running agent tasks asynchronously
"""

import asyncio
import logging
from typing import Dict, Any
from arq import create_pool, cron
from arq.connections import RedisSettings
import uvloop

from app.core.config import settings
from app.db.base import AsyncSessionLocal
from app.runtime.session_manager import session_manager
from app.runtime.workflow_engine import workflow_engine

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def startup(ctx: Dict[str, Any]):
    """Worker startup"""
    logger.info("Agent Worker starting...")
    
    # Test database connection
    try:
        async with AsyncSessionLocal() as db:
            await db.execute("SELECT 1")
        logger.info("Database connection: ✓")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
    
    # Test LLM connection
    try:
        from app.services.llm_adapter import llm_adapter
        if settings.llm_api_key:
            is_connected = await llm_adapter.test_connection()
            logger.info(f"LLM connection: {'✓' if is_connected else '✗'}")
        else:
            logger.warning("LLM_API_KEY not set")
    except Exception as e:
        logger.error(f"LLM connection test failed: {e}")


async def shutdown(ctx: Dict[str, Any]):
    """Worker shutdown"""
    logger.info("Agent Worker shutting down...")


async def execute_agent_step(
    ctx: Dict[str, Any],
    session_id: str,
    step_data: Dict[str, Any],
    context_data: Dict[str, Any],
    workflow_run_id: str,
    step_id: str,
):
    """
    Execute an agent step asynchronously
    
    Args:
        session_id: Agent session ID
        step_data: Step configuration
        context_data: Execution context
        workflow_run_id: Workflow run ID
        step_id: Step ID for callback
    """
    
    logger.info(f"Executing agent step: {step_id} for session {session_id}")
    
    try:
        async with AsyncSessionLocal() as db:
            from app.runtime.session_manager import Context
            import uuid
            
            # Reconstruct context
            context = Context(
                project_id=uuid.UUID(context_data["project_id"]),
                user_input=context_data.get("user_input"),
                upstream_artifacts=context_data.get("upstream_artifacts", []),
                director_notes=context_data.get("director_notes"),
                iteration=context_data.get("iteration", 1),
                max_iterations=context_data.get("max_iterations", 2),
            )
            
            # Execute step
            artifact = await session_manager.dispatch(
                db,
                uuid.UUID(session_id),
                context,
                step_data.get("task_type", "draft"),
            )
            
            if artifact:
                logger.info(f"Step {step_id} completed successfully, artifact: {artifact.id}")

                from app.models.workflow_run import StepExecution
                from sqlalchemy import update as sa_update
                await db.execute(
                    sa_update(StepExecution)
                    .where(
                        StepExecution.run_id == workflow_run_id,
                        StepExecution.step_id == step_id,
                    )
                    .values(status="completed")
                )
                await db.commit()
            else:
                logger.error(f"Step {step_id} failed to produce artifact")
                from app.models.workflow_run import StepExecution
                from sqlalchemy import update as sa_update
                await db.execute(
                    sa_update(StepExecution)
                    .where(
                        StepExecution.run_id == workflow_run_id,
                        StepExecution.step_id == step_id,
                    )
                    .values(status="failed")
                )
                await db.commit()

    except Exception as e:
        logger.error(f"Step {step_id} execution failed: {e}")
        async with AsyncSessionLocal() as fail_db:
            from app.models.workflow_run import StepExecution
            from sqlalchemy import update as sa_update
            try:
                await fail_db.execute(
                    sa_update(StepExecution)
                    .where(
                        StepExecution.run_id == workflow_run_id,
                        StepExecution.step_id == step_id,
                    )
                    .values(status="failed")
                )
                await fail_db.commit()
            except Exception as db_err:
                logger.error(f"Failed to update step status to failed: {db_err}")


# Periodic task to clean up old memories
@cron("0 2 * * *")  # Daily at 2 AM
async def cleanup_old_memories(ctx: Dict[str, Any]):
    """Clean up old Redis memories and session data"""
    
    logger.info("Starting memory cleanup...")
    
    try:
        from app.runtime.session_manager import session_manager
        import redis.asyncio as redis
        from datetime import datetime, timedelta
        
        # Connect to Redis
        redis_client = redis.from_url(settings.redis_url)
        
        # Get all session memory keys
        pattern = "session:*:memory"
        keys = await redis_client.keys(pattern)
        
        cleanup_count = 0
        for key in keys:
            # Check TTL
            ttl = await redis_client.ttl(key)
            if ttl == -1:  # No expiration set
                # Set TTL to 24 hours
                await redis_client.expire(key, 24 * 3600)
            elif ttl < 3600:  # Less than 1 hour remaining
                # Delete old memories
                await redis_client.delete(key)
                cleanup_count += 1
        
        await redis_client.close()
        
        logger.info(f"Memory cleanup completed, removed {cleanup_count} old sessions")
        
    except Exception as e:
        logger.error(f"Memory cleanup failed: {e}")


# Worker settings
class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    
    # Functions to register
    functions = [
        execute_agent_step,
    ]
    
    # Cron jobs
    cron_jobs = [
        cleanup_old_memories,
    ]
    
    # Worker settings
    on_startup = startup
    on_shutdown = shutdown
    
    # Job settings
    job_timeout = 300  # 5 minutes
    keep_result = 3600  # Keep results for 1 hour
    
    # Worker process settings
    max_jobs = 5
    
    # Health check
    health_check_interval = 30


async def main():
    """Run worker with uvloop for better performance"""
    
    # Use uvloop for better async performance
    uvloop.install()
    
    # Create Redis pool
    redis = await create_pool(WorkerSettings.redis_settings)
    
    # Create and run worker
    from arq import Worker
    
    worker = Worker(
        functions=WorkerSettings.functions,
        redis_pool=redis,
        on_startup=WorkerSettings.on_startup,
        on_shutdown=WorkerSettings.on_shutdown,
        cron_jobs=WorkerSettings.cron_jobs,
        job_timeout=WorkerSettings.job_timeout,
        keep_result=WorkerSettings.keep_result,
        max_jobs=WorkerSettings.max_jobs,
        health_check_interval=WorkerSettings.health_check_interval,
    )
    
    logger.info("Starting Agent Worker...")
    await worker.main()


if __name__ == "__main__":
    asyncio.run(main())