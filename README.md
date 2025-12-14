# Agentic Health Agent

This project implements a robust multi-agent system for generating Cognitive Behavioral Therapy (CBT) exercises. It is built using **LangGraph** and implements the **Model Context Protocol (MCP)**.

## Architecture & Resources

The system architecture follows the **Supervisor-Worker** pattern recommended in Anthropic's "Building Effective Agents" and LangGraph tutorials.

*   **Agents**:
    *   **Drafter**: Generates and revises content.
    *   **Safety Guardian**: Checks for risks (self-harm, medical advice).
    *   **Clinical Critic**: Reviews empathy and clinical tone.
    *   **Supervisor**: Orchestrates the workflow and decisions.
*   **State Management**: A shared "Blackboard" state persisted in SQLite.
*   **Interfaces**:
    1.  **React Dashboard**: For Human-in-the-Loop visualization and intervention.
    2.  **MCP Server**: Implements `modelcontextprotocol.io` standards for machine-to-machine integration (e.g., Claude Desktop).

## Setup

1.  **Create Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Variables**:
    Create a `.env` file in the root directory:
    ```
    OPENAI_API_KEY=sk-...
    ```

## Usage

### 1. React Dashboard (Human-in-the-Loop)
*Best for visualizing the agent thoughts and "halting" for human review.*

1.  Start the Backend:
    ```bash
    source venv/bin/activate
    python src/server.py
    ```
2.  Start the Frontend:
    ```bash
    cd frontend
    npm install
    npm run dev
    ```
3.  Open **http://localhost:5173**.

### 2. MCP Server (Claude Desktop)
*Best for automated generation within an LLM client.*

```bash
source venv/bin/activate
python src/mcp_server.py
```

**Configure Claude Desktop**:

Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "agentic-health": {
      "command": "/absolute/path/to/agentic_health_agent/venv/bin/python",
      "args": ["/absolute/path/to/agentic_health_agent/src/mcp_server.py"]
    }
  }
}
```

Replace `/absolute/path/to/` with your actual project path. For example:
```json
{
  "mcpServers": {
    "agentic-health": {
      "command": "/Users/rohitsundaram/agentic_health_agent/venv/bin/python",
      "args": ["/Users/rohitsundaram/agentic_health_agent/src/mcp_server.py"]
    }
  }
}
```

Restart Claude Desktop and prompt: *"Ask Agentic Health to create a sleep hygiene protocol."*

### 3. CLI Mode
*For simple testing.*
```bash
source venv/bin/activate
python main.py
```

## History & Persistence
All sessions are logged to `history.sqlite`. You can view past generations via the API endpoint `GET /history`.
