"""
reasoning_agent.py — DEPRECATED (root-level)

This file is kept only for backward compatibility.
The active implementation is in agents/reasoning_agent/agent.py.

Use the pipeline instead:
    from pipeline import run_pipeline
    from agents.reasoning_agent import reasoning_agent_node, wrap_node
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Re-export from the canonical location
from agents.reasoning_agent.agent import reasoning_agent_node  # noqa: F401
from agents.reasoning_agent.inclusion import wrap_node          # noqa: F401

__all__ = ["reasoning_agent_node", "wrap_node"]
