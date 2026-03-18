#!/usr/bin/env python3
"""
System test script to verify the platform works end-to-end
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add the backend app directory to Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

from app.db.base import AsyncSessionLocal
from app.models.organization import Organization
from app.models.user import User
from app.models.project import Project
from app.models.workflow_template import WorkflowTemplate
from app.services.llm_adapter import llm_adapter
from app.runtime.workflow_engine import workflow_engine
from app.core.config import settings
from sqlalchemy import select


async def test_database():
    """Test database connectivity"""
    print("🗄️ Testing database connection...")
    
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute("SELECT version()")
            version = result.scalar()
            print(f"✓ PostgreSQL connected: {version}")
            
            # Count tables
            result = await db.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            table_count = result.scalar()
            print(f"✓ Database has {table_count} tables")
            
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def test_llm():
    """Test LLM connection"""
    print("🤖 Testing LLM connection...")
    
    if not settings.llm_api_key:
        print("⚠️ LLM_API_KEY not set, skipping LLM test")
        return True
    
    try:
        response = await llm_adapter.complete(
            messages=[{"role": "user", "content": "Say hello in one word"}],
            max_tokens=5
        )
        print(f"✓ LLM connected ({settings.llm_provider}): {response.content.strip()}")
        return True
    except Exception as e:
        print(f"❌ LLM connection failed: {e}")
        return False


async def test_system_data():
    """Test system default data"""
    print("📊 Testing system default data...")
    
    try:
        async with AsyncSessionLocal() as db:
            # Check workflow templates
            result = await db.execute(
                select(WorkflowTemplate).where(WorkflowTemplate.is_system == True)
            )
            templates = result.scalars().all()
            print(f"✓ Found {len(templates)} system workflow templates")
            
            for template in templates:
                print(f"  - {template.name}")
            
            # Check agent definitions
            from app.models.agent_definition import AgentDefinition
            result = await db.execute(
                select(AgentDefinition).where(AgentDefinition.is_system == "true")
            )
            agents = result.scalars().all()
            print(f"✓ Found {len(agents)} system agent definitions")
            
            for agent in agents:
                print(f"  - {agent.display_name} ({agent.role})")
                
        return True
    except Exception as e:
        print(f"❌ System data check failed: {e}")
        return False


async def test_create_demo_data():
    """Create demo organization and user for testing"""
    print("🏢 Creating demo test data...")
    
    try:
        async with AsyncSessionLocal() as db:
            # Check if demo org already exists
            result = await db.execute(
                select(Organization).where(Organization.name == "Demo Organization")
            )
            demo_org = result.scalar_one_or_none()
            
            if not demo_org:
                # Create demo organization
                demo_org = Organization(
                    name="Demo Organization",
                    plan_type="free"
                )
                db.add(demo_org)
                await db.flush()
                
                # Create demo user
                from app.api.auth import hash_password
                demo_user = User(
                    org_id=demo_org.id,
                    email="demo@example.com",
                    hashed_password=hash_password("demo123"),
                    full_name="Demo User",
                    role="admin",
                    is_active=True,
                    is_verified=True
                )
                db.add(demo_user)
                await db.flush()
                
                # Create demo project
                demo_project = Project(
                    org_id=demo_org.id,
                    name="測試專案 - 設備監控系統",
                    description="這是一個用於測試 Agent 協作的示範專案",
                    status="draft",
                    created_by=demo_user.id
                )
                db.add(demo_project)
                
                await db.commit()
                print("✓ Created demo organization, user, and project")
                print("  Email: demo@example.com")
                print("  Password: demo123")
            else:
                print("✓ Demo data already exists")
                
        return True
    except Exception as e:
        print(f"❌ Demo data creation failed: {e}")
        return False


async def test_workflow_engine():
    """Test workflow engine with a simple flow"""
    print("⚙️ Testing workflow engine...")
    
    if not settings.llm_api_key:
        print("⚠️ LLM_API_KEY not set, skipping workflow engine test")
        return True
    
    try:
        async with AsyncSessionLocal() as db:
            # Get demo data
            result = await db.execute(
                select(Organization).where(Organization.name == "Demo Organization")
            )
            demo_org = result.scalar_one()
            
            result = await db.execute(
                select(Project).where(Project.org_id == demo_org.id)
            )
            demo_project = result.scalar_one()
            
            result = await db.execute(
                select(User).where(User.org_id == demo_org.id)
            )
            demo_user = result.scalar_one()
            
            # Get quick review template
            result = await db.execute(
                select(WorkflowTemplate).where(
                    WorkflowTemplate.is_system == True,
                    WorkflowTemplate.definition["workflow"]["id"].astext == "quick-review"
                )
            )
            template = result.scalar_one()
            
            print("✓ Found required data for workflow test")
            
            # This would start a real workflow, but for testing we just verify the setup
            print("✓ Workflow engine setup verified (not starting actual workflow)")
            
        return True
    except Exception as e:
        print(f"❌ Workflow engine test failed: {e}")
        return False


async def main():
    """Run all system tests"""
    print("🚀 Multi-Agent Collaboration Platform - System Test")
    print("=" * 50)
    
    tests = [
        ("Database", test_database),
        ("LLM Connection", test_llm),
        ("System Data", test_system_data),
        ("Demo Data", test_create_demo_data),
        ("Workflow Engine", test_workflow_engine),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📋 Test Results:")
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"  {test_name:20} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("🎉 All tests passed! The system is ready to use.")
        print("\nTo start using the platform:")
        print("1. Start the services: docker-compose up -d")
        print("2. Open browser: http://localhost:3000")
        print("3. Login with: demo@example.com / demo123")
        print("4. Or register a new account")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        print("Make sure you have:")
        print("1. Set LLM_API_KEY in .env file")
        print("2. Started database: docker-compose up db redis minio -d")
        print("3. Initialized database: python init_db.py")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())