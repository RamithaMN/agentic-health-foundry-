# ==============================================================================
# Agentic Health Agent - CLI Entry Point
# ==============================================================================
# This file serves as the command-line interface for the Agentic Health Agent.
# It initializes the LangGraph workflow, manages the SQLite checkpointing for
# persistence, and handles the interactive user session loop.
#
# Created by: Human Developer
# Last Updated: 2025
# ==============================================================================

import os
import uuid
import sqlite3
from src.graph import get_graph
from src.state import AgentState
from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver

# Load environment variables (e.g. OPENAI_API_KEY)
load_dotenv()

def main():
    """
    Main execution loop for the CLI interface.
    Initializes the agent graph in autonomous mode (no human-in-the-loop interrupts).
    """
    print("Initializing Agentic Health Agent...")
    
    # Ensure DB exists
    db_path = "checkpoints.sqlite"
    conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    
    # Run in autonomous mode for CLI (no human interrupt)
    graph = get_graph(checkpointer=checkpointer, with_interrupt=False)
    
    # Simulate a user session
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    print(f"Session ID: {thread_id}")
    
    while True:
        user_input = input("\nEnter your request (or 'q' to quit): ")
        if user_input.lower() in ['q', 'quit']:
            break
            
        initial_state = {
            "user_intent": user_input,
            "iteration_count": 0,
            "draft_history": [],
            "scratchpad": [],
            "critique_feedback": [],
            "safety_feedback": [],
            "status": "drafting"
        }
        
        print(f"\nProcessing request: {user_input}\n")
        
        # Stream events
        # We use stream_mode="values" to see state updates or "updates" for node outputs
        for event in graph.stream(initial_state, config=config):
            for key, value in event.items():
                print(f"\n--- Node: {key} ---")
                # Print specific details based on node
                if key == "drafter":
                    if value.get("current_draft"):
                        print(f"Draft Title: {value['current_draft'].title}")
                elif key == "guardian":
                    print(f"Safety Score: {value.get('safety_score')}")
                    if value.get('safety_feedback'):
                        print(f"Safety Feedback: {value['safety_feedback']}")
                elif key == "critic":
                    print(f"Empathy Score: {value.get('empathy_score')}")
                    if value.get('critique_feedback'):
                        print(f"Critique Feedback: {value['critique_feedback']}")
                elif key == "supervisor":
                    print(f"Status: {value.get('status')}")

        # Fetch final state
        final_state = graph.get_state(config)
        if final_state and final_state.values.get("current_draft"):
            draft = final_state.values["current_draft"]
            print("\n=== FINAL CBT EXERCISE ===")
            print(f"Title: {draft.title}")
            print(f"Description: {draft.description}")
            print("Steps:")
            for step in draft.steps:
                print(f"- {step}")
            print(f"Rationale: {draft.rationale}")
            if draft.safety_notes:
                print(f"Safety Notes: {draft.safety_notes}")
            print("==========================\n")
        else:
            print("\nProcess finished without a final draft (or failed).")

if __name__ == "__main__":
    main()
