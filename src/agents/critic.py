# ==============================================================================
# Agentic Health Agent - Clinical Critic
# ==============================================================================
# The Clinical Critic evaluates the content for tone, empathy, and clinical
# quality. It ensures the output feels like it came from a compassionate
# professional.
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


class ClinicalReview(BaseModel):
    is_empathetic: bool = Field(description="True if the tone is sufficiently empathetic")
    empathy_score: int = Field(description="Empathy score from 0 (cold) to 10 (very warm/supportive)")
    clinical_quality_score: int = Field(description="Quality of CBT application 0-10")
    feedback: list[str] = Field(description="Specific feedback on tone, language, and clinical validity")

def critic_agent(state: AgentState):
    """
    Reviews the draft for empathy, tone, and clinical quality.
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    print("---CLINICAL CRITIC WORKING---")
    current_draft = state["current_draft"]
    
    if not current_draft:
        return {}

    parser = JsonOutputParser(pydantic_object=ClinicalReview)
    
    system_message = """You are a Clinical Critic (Senior CBT Therapist).
    Your role is to ensure the CBT exercise is empathetic, warm, and follows best clinical practices.
    The tone should be validating and encouraging, not robotic or dismissive.
    
    Review the following exercise.
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
        
        review = ClinicalReview(**review_dict)
        
        note = AgentNote(
            agent_name="ClinicalCritic",
            content=f"Clinical Review Complete. Empathy: {review.empathy_score}, Quality: {review.clinical_quality_score}",
            timestamp=datetime.now().isoformat()
        )
        
        updates = {
            "empathy_score": review.empathy_score,
            "scratchpad": [note],
        }
        
        # If scores are low, provide detailed feedback
        if review.empathy_score < 8 or review.clinical_quality_score < 8:
            feedback_str = f"Clinical Feedback: {'; '.join(review.feedback)}"
            updates["critique_feedback"] = [feedback_str]
            
        return updates

    except Exception as e:
        print(f"Error in critic: {e}")
        return {}

