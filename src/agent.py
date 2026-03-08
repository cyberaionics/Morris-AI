"""
LangChain/LangGraph tool-calling agent for the Universal HR system.
Implements autonomous planning, tool selection, and execution with decision logging.
Uses langgraph's create_react_agent for modern LangChain compatibility.
"""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from .tools import get_all_tools

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are the Universal HR Autonomous Agent — an intelligent HR operations assistant capable of managing HR workflows across any domain (technology, finance, healthcare, marketing, manufacturing, etc.).

## Your Capabilities
You have access to tools for:
- Parsing resumes and job descriptions (any industry)
- Matching candidates to jobs with explainable scoring (0-100)
- Scheduling interviews and sending professional emails
- Managing employee onboarding checklists
- Processing leave requests and checking balances
- Searching HR policies (leave, maternity, reimbursement, remote work, etc.)
- Generating HR documents (offer letters, confirmations, etc.)
- Verifying candidate credentials by crawling resume links
- Listing available candidate resumes

## Autonomous Planning
Before executing any multi-step task, you MUST generate an internal plan:

PLAN:
1. [First step]
2. [Second step]
...

Then execute each step using the appropriate tools.

## Rules
1. Always be professional, thorough, and domain-agnostic.
2. When processing candidates, consider ALL relevant factors.
3. Provide clear explanations for scores and decisions.
4. For verification tasks, always report findings transparently.
5. When uncertain, state your confidence level.
6. Log your reasoning at each decision point.
7. Handle errors gracefully and inform the user.
8. When asked about HR policies, always use the policy_search tool.
9. When scheduling interviews, always confirm both parties.
10. Treat all employee data as confidential."""


# ---------------------------------------------------------------------------
# Agent Factory
# ---------------------------------------------------------------------------

_agent = None


def _create_agent():
    """Create the react agent with all HR tools bound."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
    tools = get_all_tools()

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )

    logger.info("HR Agent initialized with %d tools", len(tools))
    return agent


def get_agent():
    """Get or create the singleton agent instance."""
    global _agent
    if _agent is None:
        _agent = _create_agent()
    return _agent


# ---------------------------------------------------------------------------
# Message Processing
# ---------------------------------------------------------------------------

def process_message(user_message: str) -> str:
    """Process a user message through the HR agent.

    The agent will autonomously plan, select tools, and execute
    steps to fulfill the request.

    Args:
        user_message: The user's request text.

    Returns:
        The agent's final response.
    """
    logger.info("Processing message: %s", user_message[:100])
    try:
        agent = get_agent()

        result = agent.invoke({
            "messages": [HumanMessage(content=user_message)],
        })

        # Extract the final AI message
        messages = result.get("messages", [])
        if messages:
            final_msg = messages[-1]
            output = final_msg.content if hasattr(final_msg, "content") else str(final_msg)
        else:
            output = "I was unable to process your request."

        # Log tool calls for decision tracking
        tool_call_count = sum(
            1 for m in messages
            if hasattr(m, "type") and m.type == "tool"
        )
        if tool_call_count:
            logger.info("Agent completed %d tool calls", tool_call_count)

        return output

    except Exception as e:
        logger.error("Agent processing failed: %s", e, exc_info=True)
        return (
            f"I encountered an error processing your request: {str(e)}. "
            "Please try rephrasing or breaking your request into smaller steps."
        )
