# ==============================================================================
# Agentic Health Agent - LangGraph Definition
# ==============================================================================
# This module defines the state graph topology for the multi-agent system.
# It wires together the agents (Drafter, Guardian, Critic, Supervisor) and
# implements the control flow logic, including:
# - Conditional routing based on Supervisor decisions
# - Parallel execution of critique nodes
# - Human-in-the-loop interruption points
#
# Created by: Human Developer
# Last Updated: 2025
# ==============================================================================

from langgraph.graph import StateGraph, END, START
from src.state import AgentState
from src.agents.drafter import drafter_agent
from src.agents.guardian import guardian_agent
from src.agents.critic import critic_agent
from src.agents.supervisor import supervisor_node
from src.agents.human import human_review_node

# Define the graph
builder = StateGraph(AgentState)

# Add Nodes
builder.add_node("drafter", drafter_agent)
builder.add_node("guardian", guardian_agent)
builder.add_node("critic", critic_agent)
builder.add_node("supervisor", supervisor_node)
builder.add_node("human_review", human_review_node)

# Add Edges
builder.add_edge(START, "drafter")
builder.add_edge("drafter", "guardian")
builder.add_edge("drafter", "critic")
builder.add_edge("guardian", "supervisor")
builder.add_edge("critic", "supervisor")

def route_supervisor(state: AgentState):
    """
    Router function to decide next node.
    """
    status = state.get("status")
    if status == "completed":
        return "human_review" # Go to human review before end
    elif status == "failed":
        return END # Or a fail node
    elif status == "revision_needed":
        return "drafter"
    else:
        return "drafter"

def route_human(state: AgentState):
    status = state.get("status")
    if status == "approved":
        return END
    elif status == "revision_needed":
        return "drafter"
    return END

# Supervisor decides next step
builder.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {
        "drafter": "drafter",
        "human_review": "human_review",
        END: END
    }
)

# Human review routing
builder.add_conditional_edges(
    "human_review",
    route_human,
    {
        END: END,
        "drafter": "drafter"
    }
)

def get_graph(checkpointer=None, with_interrupt=True):
    """
    Returns the compiled graph with a checkpointer.
    """
    interrupt_before = ["human_review"] if with_interrupt else []
    
    return builder.compile(checkpointer=checkpointer, interrupt_before=interrupt_before)
