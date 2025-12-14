# ==============================================================================
# Agentic Health Agent - Backend API Server
# ==============================================================================
# This FastAPI server exposes the agentic workflow to the React frontend.
# It handles:
# 1. Workflow initiation (/start)
# 2. Real-time event streaming via SSE (/stream/{thread_id})
# 3. State management and persistence via AsyncSqliteSaver
# 4. Human-in-the-loop intervention (/resume/{thread_id})
#
# Created by: Human Developer
# Last Updated: 2025
# ==============================================================================

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
import uuid
import json
import asyncio
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# Load env vars
load_dotenv()

from src.graph import get_graph
from src.state import AgentState, CBTExercise
from src.history_db import init_db, create_history_entry, update_history_status, get_all_history

# Global graph variable
graph = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    # Initialize history DB
    await init_db()
    # Initialize LangGraph Checkpointer
    async with AsyncSqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
        graph = get_graph(checkpointer=checkpointer)
        yield

app = FastAPI(title="Agentic Health Agent API", lifespan=lifespan)

# Allow CORS for React app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StartRequest(BaseModel):
    intent: str

class ResumeRequest(BaseModel):
    action: str # "approve" or "revise"
    feedback: str = None
    modified_draft: dict = None

def serialize_event(event):
    """
    Helper to serialize Pydantic models in the event state.
    """
    new_event = {}
    for key, value in event.items():
        if isinstance(value, BaseModel):
            new_event[key] = value.model_dump()
        elif isinstance(value, list):
            new_list = []
            for item in value:
                if isinstance(item, BaseModel):
                    new_list.append(item.model_dump())
                else:
                    new_list.append(item)
            new_event[key] = new_list
        else:
            new_event[key] = value
    return new_event

@app.post("/start")
async def start_workflow(request: StartRequest):
    thread_id = str(uuid.uuid4())
    # Log to history
    await create_history_entry(thread_id, request.intent)
    return {"thread_id": thread_id}

@app.get("/history")
async def get_history_log():
    """
    Returns the log of all past queries and generated protocols.
    """
    return await get_all_history()

@app.get("/stream/{thread_id}")
async def stream_workflow(thread_id: str, intent: str = None):
    async def event_generator():
        config = {"configurable": {"thread_id": thread_id}}
        
        current_state = await graph.aget_state(config)
        
        inputs = None
        if not current_state.values and intent:
             # If intent provided and no state, we are starting
             inputs = {
                "user_intent": intent,
                "iteration_count": 0,
                "draft_history": [],
                "scratchpad": [],
                "critique_feedback": [],
                "safety_feedback": [],
                "status": "drafting"
            }
             await update_history_status(thread_id, "running")
        
        try:
            print(f"Starting stream for thread {thread_id} with inputs: {inputs}")
            async for event in graph.astream(inputs, config=config, stream_mode="values"):
                # Clean event for JSON serialization
                serializable_event = serialize_event(event)
                yield json.dumps(serializable_event, default=str)
                
            # Check if we stopped at interrupt
            final_snapshot = await graph.aget_state(config)
            print(f"Stream finished. Next: {final_snapshot.next}")
            
            if final_snapshot.next:
                 await update_history_status(thread_id, "paused_for_review")
                 yield json.dumps({"type": "interrupt", "next": final_snapshot.next})
            else:
                 # Check if completed successfully
                 final_values = final_snapshot.values
                 status = final_values.get("status")
                 draft = final_values.get("current_draft")
                 if status == "approved" or status == "completed":
                      await update_history_status(thread_id, "completed", artifact=draft.model_dump() if draft else None)
                 
                 yield json.dumps({"type": "completed"})
                 
        except Exception as e:
            print(f"Error in stream: {e}")
            import traceback
            traceback.print_exc()
            await update_history_status(thread_id, "error")
            yield json.dumps({"type": "error", "message": str(e)})

    return EventSourceResponse(event_generator())

@app.get("/state/{thread_id}")
async def get_state(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    state = await graph.aget_state(config)
    # Serialize state values
    return serialize_event(state.values)

@app.post("/resume/{thread_id}")
async def resume_workflow(thread_id: str, request: ResumeRequest):
    config = {"configurable": {"thread_id": thread_id}}
    
    if request.action == "approve":
        updates = {"human_approved": True}
        if request.modified_draft:
             updates["current_draft"] = CBTExercise(**request.modified_draft)
             
        await graph.aupdate_state(config, updates)
        await update_history_status(thread_id, "resumed_approved")
        
    elif request.action == "revise":
        updates = {
            "human_approved": False,
            "human_feedback": request.feedback,
            "status": "revision_needed"
        }
        await graph.aupdate_state(config, updates)
        await update_history_status(thread_id, "resumed_revise")
    
    return {"status": "updated"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
