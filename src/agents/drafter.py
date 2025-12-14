# ==============================================================================
# Agentic Health Agent - Drafter
# ==============================================================================
# The Drafter agent is responsible for creating the initial content and
# revising it based on feedback. It acts as the primary "writer" in the system.
#
# Created by: Human Developer
# Last Updated: 2025
# ==============================================================================

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from src.state import AgentState, CBTExercise, AgentNote
from datetime import datetime
import os


def drafter_agent(state: AgentState):
    """
    Drafts a CBT exercise based on user intent or revises it based on feedback.
    """
    # Initialize LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

    print("---DRAFTER AGENT WORKING---")
    user_intent = state["user_intent"]
    current_draft = state.get("current_draft")
    critique_feedback = state.get("critique_feedback", [])
    safety_feedback = state.get("safety_feedback", [])
    
    parser = PydanticOutputParser(pydantic_object=CBTExercise)
    
    if not current_draft:
        # Initial Draft
        system_message = """You are an expert CBT Therapist acting as a Drafter. 
        Your goal is to create a structured CBT exercise based on the user's intent.
        Ensure the exercise is empathetic, clear, and clinically grounded.
        
        {format_instructions}
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("user", "User Intent: {intent}")
        ])
        
        chain = prompt | llm | parser
        try:
            new_draft = chain.invoke({
                "intent": user_intent,
                "format_instructions": parser.get_format_instructions()
            })
            note = AgentNote(
                agent_name="Drafter",
                content="Created initial draft.",
                timestamp=datetime.now().isoformat()
            )
            return {
                "current_draft": new_draft,
                "draft_history": [new_draft],
                "scratchpad": [note],
                "iteration_count": state.get("iteration_count", 0) + 1,
                "status": "review_pending"
            }
        except Exception as e:
            # Fallback or error handling
            print(f"Error in drafter: {e}")
            return {"status": "failed"}
            
    else:
        # Revision
        system_message = """You are an expert CBT Therapist acting as a Drafter.
        You need to revise the current CBT exercise based on feedback from the Clinical Critic and Safety Guardian.
        
        Current Draft:
        {current_draft}
        
        Clinical Feedback:
        {critique_feedback}
        
        Safety Feedback:
        {safety_feedback}
        
        Please generate a revised version of the exercise.
        {format_instructions}
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("user", "Revise the draft based on the feedback.")
        ])
        
        chain = prompt | llm | parser
        try:
            new_draft = chain.invoke({
                "current_draft": current_draft.model_dump_json(),
                "critique_feedback": "\n".join(critique_feedback[-3:]), # Last few feedbacks
                "safety_feedback": "\n".join(safety_feedback[-3:]),
                "format_instructions": parser.get_format_instructions()
            })
            
            note = AgentNote(
                agent_name="Drafter",
                content="Revised draft based on feedback.",
                timestamp=datetime.now().isoformat()
            )
            
            return {
                "current_draft": new_draft,
                "draft_history": [new_draft],
                "scratchpad": [note],
                "iteration_count": state["iteration_count"] + 1,
                "status": "review_pending"
            }
        except Exception as e:
            print(f"Error in drafter revision: {e}")
            return {"status": "failed"}

