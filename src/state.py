# ==============================================================================
# Agentic Health Agent - State Definition
# ==============================================================================
# Defines the shared state ("The Blackboard") used by all agents in the graph.
# It uses Pydantic models for structured data validation and TypedDict for
# LangGraph state management.
#
# Created by: Human Developer
# Last Updated: 2025
# ==============================================================================

import operator
from typing import Annotated, List, Optional, Dict, Any, TypedDict, Union
from pydantic import BaseModel, Field

class CBTExercise(BaseModel):
    title: str = Field(description="Title of the CBT exercise")
    description: str = Field(description="Brief description of the exercise")
    steps: List[str] = Field(description="Step-by-step instructions for the user")
    rationale: str = Field(description="Clinical rationale for why this exercise helps")
    safety_notes: Optional[str] = Field(default=None, description="Important safety warnings")

class AgentNote(BaseModel):
    agent_name: str
    content: str
    timestamp: str

class AgentState(TypedDict):
    # The user's original intent
    user_intent: str
    
    # The evolving draft of the CBT exercise
    current_draft: Optional[CBTExercise]
    
    # History of drafts to track versions
    draft_history: Annotated[List[CBTExercise], operator.add]
    
    # Shared scratchpad for agent communication
    scratchpad: Annotated[List[AgentNote], operator.add]
    
    # Metadata
    iteration_count: int
    safety_score: Optional[int] # 0-10 or similar
    empathy_score: Optional[int] # 0-10 or similar
    
    # Current status/stage
    status: str # "drafting", "reviewing", "critiquing", "completed", "failed", "pending_review"
    
    # Feedback from critics
    critique_feedback: Annotated[List[str], operator.add]
    safety_feedback: Annotated[List[str], operator.add]
    
    # Final output message to user
    final_output: Optional[str]
    
    # Human Feedback
    human_feedback: Optional[str]
    human_approved: Optional[bool]
