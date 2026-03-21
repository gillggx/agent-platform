"""Database seed data for system defaults"""

from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.agent_definition import AgentDefinition
from app.models.workflow_template import WorkflowTemplate
from app.models.organization import Organization
from app.models.user import User
from app.data.default_templates import DEFAULT_TEMPLATES
from app.api.auth import DEFAULT_ORG_ID, DEFAULT_USER_ID

SOULS_DIR = Path(__file__).parent.parent.parent / "souls"


def _load_soul(role: str) -> str:
    """Load soul content from souls/{role}.md file"""
    soul_file = SOULS_DIR / f"{role}.md"
    if soul_file.exists():
        return soul_file.read_text(encoding="utf-8")
    return ""


# Default agent definitions (system-wide)
DEFAULT_AGENTS = [
    {
        "role": "pm",
        "display_name": "PM Agent",
        "description": "產品經理Agent，負責需求分析和產品規格撰寫",
        "config": {"temperature": 0.7, "max_tokens": 4096},
    },
    {
        "role": "architect",
        "display_name": "Architect Agent", 
        "description": "架構師Agent，負責技術方案設計和架構審核",
        "config": {"temperature": 0.6, "max_tokens": 4096},
    },
    {
        "role": "devops",
        "display_name": "DevOps Agent",
        "description": "DevOps Agent，負責部署方案和營運考量",
        "config": {"temperature": 0.6, "max_tokens": 4096},
    },
    {
        "role": "qa",
        "display_name": "QA Agent",
        "description": "測試Agent，負責測試計畫和品質確保",
        "config": {"temperature": 0.5, "max_tokens": 4096},
    },
    {
        "role": "director",
        "display_name": "Director Agent",
        "description": "總監Agent，負責最終審核和決策",
        "config": {"temperature": 0.3, "max_tokens": 2048},
    },
    {
        "role": "pm_critic",
        "display_name": "PM Critic Agent",
        "description": "魔鬼代言人PM，透過嚴格挑戰完善產品規格",
        "config": {"temperature": 0.7, "max_tokens": 2048},
    },
]


async def seed_demo_org_and_user(db: AsyncSession):
    """Create demo organization and user"""
    
    # Check if org exists
    result = await db.execute(
        select(Organization).where(Organization.id == DEFAULT_ORG_ID)
    )
    org = result.scalar_one_or_none()
    
    if not org:
        org = Organization(
            id=DEFAULT_ORG_ID,
            name="Demo Organization",
            plan_type="free",
        )
        db.add(org)
        print("Created demo organization")
    
    # Check if user exists
    result = await db.execute(
        select(User).where(User.id == DEFAULT_USER_ID)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            id=DEFAULT_USER_ID,
            org_id=DEFAULT_ORG_ID,
            email="demo@example.com",
            hashed_password="not-used",
            full_name="Demo User",
            role="admin",
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        print("Created demo user")
    
    await db.commit()


async def seed_system_agents(db: AsyncSession):
    """Create system default agent definitions"""
    
    for agent_data in DEFAULT_AGENTS:
        # Check if agent already exists
        result = await db.execute(
            select(AgentDefinition).where(
                AgentDefinition.role == agent_data["role"],
                AgentDefinition.is_system == "true",
            )
        )
        existing_agent = result.scalar_one_or_none()
        
        soul_content = _load_soul(agent_data["role"])

        if not existing_agent:
            agent = AgentDefinition(
                org_id=None,
                role=agent_data["role"],
                display_name=agent_data["display_name"],
                description=agent_data["description"],
                knowledge_pack_id=None,
                soul=soul_content,
                config=agent_data["config"],
                is_system="true",
            )
            db.add(agent)
            print(f"Created system agent: {agent_data['display_name']}")
        elif soul_content:
            # Always sync soul from file so edits to .md take effect on restart
            existing_agent.soul = soul_content
            print(f"Synced soul for: {agent_data['display_name']}")

    await db.commit()


async def seed_workflow_templates(db: AsyncSession):
    """Create system default workflow templates"""
    
    for template_data in DEFAULT_TEMPLATES:
        template_name = template_data["workflow"]["name"]
        
        # Check if template with same name already exists
        result = await db.execute(
            select(WorkflowTemplate).where(
                WorkflowTemplate.name == template_name,
                WorkflowTemplate.is_system == True,
            )
        )
        existing_template = result.scalar_one_or_none()
        
        if not existing_template:
            template = WorkflowTemplate(
                org_id=None,
                name=template_name,
                description=template_data["workflow"]["description"],
                definition=template_data,
                is_system=True,
            )
            db.add(template)
            print(f"Created system template: {template_name}")
        else:
            # Always update definition so template changes take effect on restart
            existing_template.definition = template_data
            existing_template.description = template_data["workflow"]["description"]
            print(f"Updated system template: {template_name}")
    
    await db.commit()


async def seed_all_defaults(db: AsyncSession):
    """Seed all default system data"""
    
    print("Seeding system default data...")
    
    await seed_demo_org_and_user(db)
    await seed_system_agents(db)
    await seed_workflow_templates(db)
    
    print("System defaults seeded successfully!")
