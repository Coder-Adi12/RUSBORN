import inspect

import pytest
import tiktoken

from agent import DefaultAgent
from agent_core.context import CallContext
from agent_core.prompts import build_system_prompt
from agent_core.tools import AppointmentTools


def test_prompt_context_injection():
    ctx = CallContext(
        customer_id="cust-123",
        call_id="call-456",
        campaign_id="camp-789",
        direction="outbound",
        customer_name="Alice Smith",
        company="Acme Corp",
        description="Looking for AI solutions",
        customer_context="Met at tradeshow, likes green tea."
    )
    prompt = build_system_prompt(ctx)

    assert "Alice Smith" in prompt
    assert "Acme Corp" in prompt
    assert "Looking for AI solutions" in prompt
    assert "Met at tradeshow, likes green tea." in prompt
    assert "Do not reveal that you received their information from a database" in prompt
    assert "cust-123" not in prompt
    assert "call-456" not in prompt
    assert "camp-789" not in prompt
    assert "outbound" in prompt.lower()

def test_prompt_inbound_injection():
    ctx = CallContext(direction="inbound")
    prompt = build_system_prompt(ctx)

    assert "inbound call" in prompt.lower()
    assert "outbound call" not in prompt.lower()

def test_prompt_no_context():
    prompt = build_system_prompt()
    assert "No customer context provided." in prompt

def test_prompt_token_budget():
    """Verify that the system prompt + tool definitions stay well below the 1600 token baseline."""
    try:
        enc = tiktoken.get_encoding('cl100k_base')
    except Exception:
        pytest.skip("tiktoken not installed")

    sys_prompt = build_system_prompt()
    sys_toks = len(enc.encode(sys_prompt))

    tools = AppointmentTools(CallContext())
    tools_text = ''
    for name, method in inspect.getmembers(tools, predicate=inspect.ismethod):
        if hasattr(method, '__doc__') and method.__doc__:
            tools_text += method.__doc__ + '\n'
        if hasattr(method, '__llm_function__'):
            tools_text += method.__llm_function__.description + '\n'

    tool_toks = len(enc.encode(tools_text))

    agent = DefaultAgent(CallContext())
    endcall_toks = 0
    for t in agent.tools:
        if type(t).__name__ == 'EndCallTool':
            endcall_toks = len(enc.encode("End the call when the customer says goodbye or asks to stop. End the conversation naturally and briefly."))
            break

    tool_toks += endcall_toks
    total_static_tokens = sys_toks + tool_toks

    # The old baseline was ~1842. We want to be strictly smaller.
    assert sys_toks < 1100, f"System prompt must be < 1100 tokens (was {sys_toks})"
    assert total_static_tokens < 1200, f"Total static tokens must be < 1200 (was {total_static_tokens})"
