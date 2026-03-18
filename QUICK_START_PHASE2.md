# Phase 2 Quick Start Guide

## 🚀 Getting Started with Phase 2

### Import the Modules

```python
# LLM Integration
from app.intelligence import (
    LLMAdapterV2,
    LLMConfig,
    ModelRouter,
    ComplexityLevel,
    ROLE_COMPLEXITY_MAP,
)

# Conversations
from app.intelligence import (
    AgentConversation,
    ConversationContext,
    ConversationManager,
    Message,
    MessageType,
)

# Roles & Knowledge
from app.knowledge import (
    RoleRegistry,
    RoleTemplate,
    KnowledgeBase,
    PromptFactory,
    DecisionStyle,
)

# Routing
from app.core.dynamic_routing import (
    DynamicRouter,
    RoutingContext,
    RoutingDecision,
)
```

---

## 📝 5-Minute Examples

### 1. Use LLM for Content Generation

```python
from app.intelligence import LLMAdapterV2, LLMConfig

# Setup
config = LLMConfig(
    default_provider="openai",
    default_model="gpt-4o-mini",
)
adapter = LLMAdapterV2(config)

# Generate content
response = await adapter.complete(
    prompt="Write test cases for a cache layer",
    role="qa",  # Maps to SIMPLE complexity
    context={
        "requirements": "Must handle 10k RPS",
        "components": "Redis, Cache-aside pattern",
    },
)

print(response.content)
print(f"Cost: ${response.usage.cost_usd:.4f}")
```

### 2. Start a Multi-Agent Conversation

```python
from app.intelligence import AgentConversation, MessageType

# Create conversation
conv = AgentConversation(
    initiator_role="pm",
    agent_roles=["pm", "architect", "qa", "devops"],
)
await conv.start()

# PM presents requirement
await conv.agent_say(
    role="pm",
    message="Build a real-time analytics dashboard",
    message_type=MessageType.REQUEST,
)

# Architect responds
await conv.agent_say(
    role="architect",
    message="Use event streaming + time-series DB",
    message_type=MessageType.RESPONSE,
)

# Check state
state = conv.get_conversation_state()
print(f"Turn {state['current_turn']}: {state['message_count']} messages")
```

### 3. Get Prompts for Different Roles

```python
from app.knowledge import PromptFactory, RoleRegistry

# Get role info
registry = RoleRegistry()
architect = registry.get_role("architect")
print(f"{architect.display_name}: {architect.description}")

# Generate prompts
factory = PromptFactory()

# System prompt (soul prompt)
sys_prompt = factory.build_system_prompt("architect")

# Task-specific prompt
task_prompt = factory.build_task_prompt(
    role="architect",
    task="Design a microservices architecture",
    context={"scale": "1M users", "latency_budget": "100ms"},
)

# Review prompt for decision making
review_prompt = factory.build_review_prompt(
    role="director",
    artifact="architecture_document.md",
    context={"approval_criteria": "Scalability, cost-efficiency"},
)
```

### 4. Make Routing Decisions

```python
from app.core.dynamic_routing import DynamicRouter, RoutingContext

# Create router
router = DynamicRouter(llm_adapter=adapter)

# Current state after architect finishes
ctx = RoutingContext(
    current_role="architect",
    step_id="design_review",
    workflow_id="wf_analytics",
    available_next_roles=["qa", "devops", "director"],
    execution_state={"design_complete": True, "reviewed": True},
)

# Get routing decision
decision = await router.decide(ctx)

if decision.should_execute:
    print(f"Route to: {decision.next_role}")
    print(f"Confidence: {decision.confidence:.1%}")
    print(f"Reason: {decision.reasoning}")
else:
    print("Stop execution")
```

### 5. Manage Knowledge Base

```python
from app.knowledge import KnowledgeBase, KnowledgeDocument

# Create knowledge base
kb = KnowledgeBase()

# Add documents
doc = KnowledgeDocument(
    doc_id="testing_best_practices",
    title="Testing Best Practices",
    content="Always write unit tests before implementation...",
    tags=["testing", "qa", "best_practices"],
    role_relevant=["qa"],
)
kb.add_document(doc, role="qa")

# Retrieve documents
results = kb.retrieve(
    query="unit testing",
    role="qa",
    limit=5,
)

for doc in results:
    print(f"- {doc.title}")
```

---

## 🔌 Integration Points

### With WorkflowEngine

```python
from app.core.workflow_engine import WorkflowEngine, StepContext
from app.intelligence import LLMAdapterV2, LLMConfig
from app.core.dynamic_routing import DynamicRouter

# Initialize Phase 2 components
llm_config = LLMConfig()
llm_adapter = LLMAdapterV2(llm_config)
router = DynamicRouter(llm_adapter=llm_adapter)

# Use with WorkflowEngine
engine = WorkflowEngine()
engine.llm_adapter = llm_adapter  # Inject into engine
engine.router = router  # Use for dynamic decisions

# Execute workflow with LLM integration
result = await engine.execute(workflow_def)
```

### With AgentOrchestrator

```python
from app.core.agent_orchestrator import AgentOrchestrator
from app.intelligence import AgentConversation, LLMAdapterV2

# Create orchestrator with Phase 2 components
orchestrator = AgentOrchestrator()

# Start conversation within orchestrator
conv = AgentConversation(
    initiator_role="pm",
    agent_roles=orchestrator.list_agent_roles(),
)

# Agents use LLM for generation
llm_adapter = LLMAdapterV2()
agent_output = await llm_adapter.complete(
    prompt=agent_task,
    role=agent.role,
)
```

---

## 📊 Configuration Examples

### LLM Configuration

```python
from app.intelligence import LLMConfig

# Basic
config = LLMConfig()

# Custom settings
config = LLMConfig(
    default_provider="anthropic",
    default_model="claude-3-5-sonnet-20241022",
    timeout_seconds=120,
    max_retries=5,
    rate_limit_rpm=200,
    enable_caching=True,
)

# Add API keys
config.set_api_key("openai", "sk-...")
config.set_api_key("anthropic", "sk-ant-...")

adapter = LLMAdapterV2(config)
```

### Role-Specific Configuration

```python
from app.knowledge import RoleRegistry

registry = RoleRegistry()

# Get role and check capabilities
qa = registry.get_role("qa")
print(qa.capabilities)  # ['test_planning', 'validation', ...]
print(qa.tools)  # ['test_framework', 'bug_tracker']
print(qa.decision_style)  # DecisionStyle.THOROUGH

# Get all roles
all_roles = registry.list_roles()
for role in all_roles:
    print(f"{role.display_name}: {role.description}")
```

---

## 🧪 Testing Your Integration

### Simple Test

```python
# test_my_integration.py
import pytest
from app.intelligence import LLMAdapterV2, AgentConversation
from app.core.dynamic_routing import DynamicRouter

@pytest.mark.asyncio
async def test_llm_adapter():
    adapter = LLMAdapterV2()
    selection = adapter.select_model(role="architect")
    assert selection.model_id is not None
    assert selection.complexity_level.value == "complex"

@pytest.mark.asyncio
async def test_conversation():
    conv = AgentConversation("pm", ["pm", "architect"])
    await conv.start()
    msg = await conv.agent_say("pm", "Test", MessageType.REQUEST)
    assert msg.from_role == "pm"

@pytest.mark.asyncio
async def test_routing():
    router = DynamicRouter()
    decision = await router.decide(routing_context)
    assert decision is not None
    assert decision.confidence > 0.0
```

Run tests:
```bash
pytest tests/test_phase2_integration.py -v
```

---

## 🔍 Common Tasks

### Task: Generate Requirements Document

```python
async def generate_requirements():
    llm = LLMAdapterV2()
    
    response = await llm.complete(
        prompt="""Generate detailed requirements for a user authentication system.
        Include functional and non-functional requirements.""",
        role="pm",
        context={"project": "SaaS Platform"},
    )
    
    return response.content
```

### Task: Design System Architecture

```python
async def design_architecture():
    factory = PromptFactory()
    llm = LLMAdapterV2()
    
    # Get system prompt for architect
    system = factory.build_system_prompt("architect")
    
    # Build task prompt with requirements
    task = factory.build_task_prompt(
        role="architect",
        task="Design system architecture",
        context={"requirements": requirements_doc},
    )
    
    response = await llm.complete(
        prompt=task,
        role="architect",
        system_prompt=system,
    )
    
    return response.content
```

### Task: Create Test Strategy

```python
async def create_test_strategy():
    kb = KnowledgeBase()
    factory = PromptFactory(knowledge_base=kb)
    llm = LLMAdapterV2()
    
    task = factory.build_task_prompt(
        role="qa",
        task="Create comprehensive test strategy",
        context={"architecture": architecture_doc},
    )
    
    response = await llm.complete(
        prompt=task,
        role="qa",
    )
    
    return response.content
```

### Task: Multi-Round Conversation

```python
async def conduct_requirements_discussion():
    conv = AgentConversation(
        initiator_role="pm",
        agent_roles=["pm", "architect", "qa"],
    )
    await conv.start()
    
    # Round 1: PM presents initial requirements
    await conv.agent_say(
        role="pm",
        message="Build a REST API for e-commerce",
        message_type=MessageType.REQUEST,
    )
    
    # Round 2: Architect asks clarifications
    await conv.agent_say(
        role="architect",
        message="What's the expected scale?",
        message_type=MessageType.FEEDBACK,
    )
    
    # Round 3: PM clarifies
    await conv.agent_say(
        role="pm",
        message="1M users, 10k RPS peak",
        message_type=MessageType.UPDATE,
    )
    
    # Get final conversation state
    return conv.get_conversation_state()
```

---

## 🐛 Debugging Tips

### Check Model Selection

```python
router = ModelRouter(LLMConfig())

# See which model is selected
selection = router.select_model(role="director")
print(f"Model: {selection.model_id}")
print(f"Provider: {selection.provider}")
print(f"Reason: {selection.reason}")
print(f"Alternatives: {selection.alternatives}")
```

### Inspect Conversation State

```python
conv = AgentConversation("pm", ["pm", "architect"])
await conv.start()
await conv.agent_say("pm", "Test", MessageType.REQUEST)

# Get detailed state
state = conv.get_conversation_state()
for key, value in state.items():
    print(f"{key}: {value}")

# Get message history
history = conv.get_message_history()
for msg in history:
    print(f"{msg.from_role}: {msg.content[:50]}...")
```

### Analyze Routing Decision

```python
router = DynamicRouter()
decision = await router.decide(routing_context)

print(f"Should Execute: {decision.should_execute}")
print(f"Next Role: {decision.next_role}")
print(f"Confidence: {decision.confidence:.1%}")
print(f"Reasoning: {decision.reasoning}")

# Explain in human-readable format
explanation = router.explain_decision(decision)
print(explanation)
```

---

## 📚 Additional Resources

- **Full Documentation:** See `PHASE_2_SUMMARY.md`
- **Detailed Checklist:** See `IMPLEMENTATION_CHECKLIST.md`
- **Test Examples:** See `tests/test_phase2_integration.py`
- **API Reference:** Check docstrings in each module

---

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| LLM API key not found | Set in LLMConfig: `config.set_api_key("openai", "sk-...")` |
| Conversation not starting | Call `await conv.start()` after creating |
| Message not received | Use `broadcast_to_agents()` with handler callback |
| Routing decision empty | Ensure `available_next_roles` is not empty |
| Knowledge retrieval returns nothing | Check `role_relevant` field in documents |

---

## Next Steps

1. **Review** the example code above
2. **Run** the tests: `pytest tests/test_phase2_integration.py -v`
3. **Integrate** with your Phase 1 WorkflowEngine
4. **Test** with real workflows
5. **Prepare** for Phase 3 (document generation)

Happy coding! 🚀

