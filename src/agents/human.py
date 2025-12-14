# ==============================================================================
# Agentic Health Agent - Human Review Node
# ==============================================================================
# This node represents the "human-in-the-loop" checkpoint. It doesn't perform
# autonomous actions but serves as a pause point where the system waits for
# external input (approval or feedback) via the API.
#
# Created by: Human Developer
# Last Updated: 2025
# ==============================================================================

from src.state import AgentState, AgentNote
from datetime import datetime

def human_review_node(state: AgentState):
    """
    Node that represents the human review step.
    This node doesn't do much itself, but serves as a checkpoint 
    where the graph can be interrupted.
    """
    print("---HUMAN REVIEW NODE---")
    
    # Check if human approved
    if state.get("human_approved"):
        return {
            "status": "approved",
            "scratchpad": [AgentNote(
                agent_name="Human",
                content="Human approved the draft.",
                timestamp=datetime.now().isoformat()
            )]
        }
    elif state.get("human_feedback"):
         return {
            "status": "revision_needed",
            "scratchpad": [AgentNote(
                agent_name="Human",
                content=f"Human feedback: {state['human_feedback']}",
                timestamp=datetime.now().isoformat()
            )],
            "critique_feedback": [f"Human Reviewer: {state['human_feedback']}"]
        }
    
    # If we got here without approval or feedback, it's just passing through 
    # (likely before the interrupt happens, or after resume if no inputs provided correctly)
    return {}


