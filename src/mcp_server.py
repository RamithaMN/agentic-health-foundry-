# ==============================================================================
# Agentic Health Agent - Model Context Protocol (MCP) Server
# ==============================================================================
# This server implements the Model Context Protocol to expose the agentic
# workflow as a tool ('create_cbt_exercise') to MCP clients like Claude Desktop.
#
# Key Features:
# - Registers the 'create_cbt_exercise' tool
# - Runs the LangGraph workflow in autonomous mode (no interrupts)
# - Handles persistence and history logging
# - Formats the final output for the LLM client
#
# Created by: Human Developer
# Last Updated: 2025
# ==============================================================================

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from src.graph import get_graph
from src.state import CBTExercise
from src.history_db import create_history_entry, update_history_status, init_db
import uuid
from dotenv import load_dotenv
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# Load env vars from project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(project_root, ".env"))

server = Server("agentic-health-agent")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="create_cbt_exercise",
            description="Create a comprehensive Cognitive Behavioral Therapy (CBT) exercise based on a user intent.",
            inputSchema={
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "description": "The user's request or intent for the exercise (e.g., 'Exposure hierarchy for agoraphobia')",
                    }
                },
                "required": ["intent"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name != "create_cbt_exercise":
        raise ValueError(f"Unknown tool: {name}")

    intent = arguments.get("intent")
    if not intent:
        raise ValueError("Intent is required")

    # Initialize DBs if needed (safe to call repeatedly)
    await init_db()

    # MONKEY PATCH: Fix for 'Connection' object has no attribute 'is_alive' in langgraph-checkpoint-sqlite
    import aiosqlite
    if not hasattr(aiosqlite.Connection, 'is_alive'):
        def is_alive(self):
            # Check if the internal thread is running (common in aiosqlite)
            return getattr(self, "_running", True)
        setattr(aiosqlite.Connection, "is_alive", is_alive)

    # Create thread and history
    thread_id = str(uuid.uuid4())
    await create_history_entry(thread_id, intent)
    await update_history_status(thread_id, "running_mcp")
    
    config = {"configurable": {"thread_id": thread_id}}
    
    inputs = {
        "user_intent": intent,
        "iteration_count": 0,
        "draft_history": [],
        "scratchpad": [],
        "critique_feedback": [],
        "safety_feedback": [],
        "status": "drafting"
    }

    try:
        # Redirect stdout to stderr to prevent breaking MCP JSON-RPC protocol with agent prints
        old_stdout = sys.stdout
        sys.stdout = sys.stderr
        
        try:
            # Use AsyncSqliteSaver for persistence
            db_path = os.path.join(project_root, "checkpoints.sqlite")
            async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
                # Initialize Graph with checkpointer and NO interrupt for autonomous execution
                graph = get_graph(checkpointer=checkpointer, with_interrupt=False)
                
                # Execute graph to completion
                final_state = await graph.ainvoke(inputs, config=config)
        finally:
            # Restore stdout
            sys.stdout = old_stdout
        
        draft = final_state.get("current_draft")
        if not draft:
            await update_history_status(thread_id, "failed_mcp")
            return [types.TextContent(type="text", text="Failed to generate a valid CBT exercise.")]
        
        await update_history_status(thread_id, "completed_mcp", artifact=draft.model_dump())
        
        # Format the output
        steps_text = '\n'.join([f'{i+1}. {step}' for i, step in enumerate(draft.steps)])
        output_text = f"""
# {draft.title}

{draft.description}

## Rationale
{draft.rationale}

## Steps
{steps_text}

## Safety Notes
{draft.safety_notes or 'None'}
"""
        return [types.TextContent(type="text", text=output_text)]
        
    except Exception as e:
        import traceback
        traceback.print_exc() # This will go to stderr because we redirected stdout to stderr
        await update_history_status(thread_id, "error_mcp")
        # Ensure stdout is restored if exception happened before inner try/finally
        if sys.stdout != sys.__stdout__ and hasattr(sys, '__stdout__'):
             sys.stdout = sys.__stdout__
        return [types.TextContent(type="text", text=f"Error executing agent: {str(e)}")]

async def main():
    # Run the server using stdin/stdout streams
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="agentic-health-agent",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
