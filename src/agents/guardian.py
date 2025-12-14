# ==============================================================================
# Agentic Health Agent - Safety Guardian
# ==============================================================================
# The Safety Guardian checks for risks such as self-harm, medical advice,
# and dangerous instructions. It acts as a safety filter before any content
# is approved.
#
# Created by: Human Developer
# Last Updated: 2025
# ==============================================================================

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from src.state import AgentState, AgentNote
from datetime import datetime
from pydantic import BaseModel, Field


class SafetyReview(BaseModel):
    is_safe: bool = Field(description="True if the exercise is safe, False otherwise")
    safety_score: int = Field(description="Safety score from 0 (dangerous) to 10 (very safe)")
    issues: list[str] = Field(description="List of safety issues identified")
    recommendations: list[str] = Field(description="Recommendations to improve safety")

def guardian_agent(state: AgentState):
    """
    Checks the current draft for safety issues (self-harm, medical advice, dangerous exposure).
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
    print("---SAFETY GUARDIAN WORKING---")
    current_draft = state["current_draft"]
    
    if not current_draft:
        return {}

    parser = JsonOutputParser(pydantic_object=SafetyReview)
    
    system_message = """You are the Safety Guardian for a CBT app.
    Your job is to rigorously review CBT exercises for potential risks.
    
    Look out for:
    1. Instructions that might lead to self-harm.
    2. Exercises that encourage dangerous behavior (e.g., exposure therapy that is too extreme).
    3. Medical advice that the system is not qualified to give.
    4. Lack of appropriate trigger warnings or safety abort protocols.
    
    IMPORTANT CONTEXT:
    - Standard CBT exposure exercises (e.g., facing fears) are clinically valid and NOT considered "dangerous behavior" unless they involve physical harm or extreme risk without professional supervision.
    - Anxiety induction is part of the process; do not flag normal anxiety-provoking steps as unsafe unless they are physically dangerous.
    - If the exercise is a standard clinical protocol (like an exposure hierarchy), it is generally safe if it includes a note about stopping if overwhelmed.
    
    Review the following exercise and provide a safety assessment.
    {format_instructions}
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("user", "Exercise to review:\n{exercise}")
    ])
    
    chain = prompt | llm | parser
    
    try:
        review_dict = chain.invoke({
            "exercise": current_draft.model_dump_json(),
            "format_instructions": parser.get_format_instructions()
        })
        
        # Validate with pydantic
        review = SafetyReview(**review_dict)
        
        note = AgentNote(
            agent_name="SafetyGuardian",
            content=f"Safety Check Complete. Safe: {review.is_safe}, Score: {review.safety_score}",
            timestamp=datetime.now().isoformat()
        )
        
        updates = {
            "safety_score": review.safety_score,
            "scratchpad": [note],
        }
        
        if not review.is_safe or review.safety_score < 8:
            feedback_str = f"Safety Issues: {'; '.join(review.issues)}. Recommendations: {'; '.join(review.recommendations)}"
            updates["safety_feedback"] = [feedback_str]
        
        return updates

    except Exception as e:
        print(f"Error in guardian: {e}")
        return {}

