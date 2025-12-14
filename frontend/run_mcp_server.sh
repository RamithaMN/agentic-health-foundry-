#!/bin/bash
cd "$(dirname "$0")"
PYTHONPATH=. python src/mcp_server.py
