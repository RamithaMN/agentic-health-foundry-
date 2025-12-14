# ==============================================================================
# Agentic Health Agent - Supervisor
# ==============================================================================
# The Supervisor acts as the router and decision maker. It aggregates reviews
# from the Guardian and Critic and decides whether to:
# 1. Request a revision (loop back to Drafter)
# 2. Approve the draft (send to Human Review)
# 3. Fail safely (if max iterations reached)
#
# Created by: Human Developer
# Last Updated: 2025
# ==============================================================================

from src.state import AgentState, AgentNote
from datetime import datetime

MAX_ITERATIONS = 3

def supervisor_node(state: AgentState):
    """
    Supervisor reviews the state and decides the next step.
    This node effectively aggregates the reviews and sets the status.
    """
    print("---SUPERVISOR WORKING---")
    
    iteration_count = state.get("iteration_count", 0)
    safety_score = state.get("safety_score", 0)
    empathy_score = state.get("empathy_score", 0)
    
    # Defaults if scores are None (first pass or error)
    if safety_score is None: safety_score = 0
    if empathy_score is None: empathy_score = 0
    
    status = "drafting"
    
    if iteration_count >= MAX_ITERATIONS:
        # Stop if we hit the limit. 
        # Check if it's "good enough" or just fail safely.
        if safety_score >= 8:
            status = "completed"
            content = "Max iterations reached. Proceeding with current draft as it is safe."
        else:
            status = "failed"
            content = "Max iterations reached. Draft is unsafe. Aborting."
    
    elif safety_score >= 8 and empathy_score >= 8:
        status = "completed"
        content = "Draft approved by Supervisor."
        
    else:
        status = "revision_needed"
        content = f"Draft needs revision. Safety: {safety_score}, Empathy: {empathy_score}"
        
    note = AgentNote(
        agent_name="Supervisor",
        content=content,
        timestamp=datetime.now().isoformat()
    )
    
    return {
        "status": status,
        "scratchpad": [note]
    }

def route_supervisor(state: AgentState):
    """
    Router function to decide next node.
    """
    status = state.get("status")
    if status == "completed":
        return "end"
    elif status == "failed":
        return "end" # Or a fail node
    elif status == "revision_needed":
        return "drafter"
    else:
        # If status is somehow unknown, default to drafter or end to prevent infinite loops?
        # But 'review_pending' should have been handled by the fact that we just ran supervisor.
        # If we came from Drafter, we are in 'review_pending'. 
        # Wait, the graph structure matters here.
        return "drafter"


