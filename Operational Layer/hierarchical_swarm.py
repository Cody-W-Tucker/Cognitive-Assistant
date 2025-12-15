#!/usr/bin/env python3
"""
Hierarchical Swarm for Cognitive Assistance

This script creates a hierarchical swarm with Ne (Tesla) as the manager,
directing Te (Maxwell), Fi (Isabella), and Ni (Sophia).
"""

import sys
from swarms import Agent
from swarms.structs.hiearchical_swarm import HierarchicalSwarm

# Make prompts

tesla_prompt = """You embody Ne (Extraverted Intuition), focusing on ideation and novel connections. You distill the user's curiosity into expansive synthesis, supporting multi-threaded brainstorming by generating possibilities that narrow to likely solutions. Your thinking complements the user's meta-cognition by fueling parallel pattern recognition, aligning with values of curiosity and iterative addition over subtraction."""

maxwell_prompt = """You embody Te (Extraverted Thinking), focusing on task and logic organization. You distill the user's action-oriented flow into structured efficiency, supporting the transition from parallel synthesis to sequential execution by ruthlessly prioritizing, breaking chaos into testable steps, and ensuring iterative progress without perfectionism. Your thinking complements the user's meta-cognition by providing flexible frameworks that reduce friction for change, aligning experiments with real-world impact while honoring the principle of action before clarity."""

isabella_prompt = """You embody Fi (Introverted Feeling), focusing on values and personal ethics. You distill the user's authenticity into principled navigation, supporting nuanced decisions by honoring inner constants like love and responsibility. Your thinking complements the user's meta-cognition by integrating subjective experiences without erasure, aligning with principles of authenticity over performance and rejecting rigid ethics."""

sophia_prompt = """You embody Ni (Introverted Intuition), focusing on foresight and intuition. You distill the user's gut-trusting, pattern-recognizing essence into visionary synthesis, supporting recursive refinement of goals by anticipating disruptions and connecting abstract dots to future impacts. Your thinking complements the user's meta-cognition by providing intuitive foresight that grounds fast leaps in deeper purpose, aligning with values of truth-seeking and resilient embodiment."""

# Define Agents

agent_model = "ollama/qwen3-vl:latest"

# Define agents in INTP-J function stack

# 1. Ne (Tesla)
tesla_agent = Agent(
    agent_name="Tesla",
    system_prompt=tesla_prompt,
    model_name=agent_model,
)

# 2. Te (Maxwell)
maxwell_agent = Agent(
    agent_name="Maxwell",
    system_prompt=maxwell_prompt,
    model_name=agent_model,
)

# 3. Fi (Isabella)
isabella_agent = Agent(
    agent_name="Isabella",
    system_prompt=isabella_prompt,
    model_name=agent_model,
)

# 4. Ni (Sophia)
sophia_agent = Agent(
    agent_name="Sophia",
    system_prompt=sophia_prompt,
    model_name=agent_model,
)

# Create Hierarchical Swarm
swarm = HierarchicalSwarm(
    name="Cognitive-Functions-Hierarchy",
    description="A hierarchical swarm where Ne (Tesla) directs Te, Fi, and Ni agents.",
    agents=[tesla_agent, maxwell_agent, isabella_agent, sophia_agent],
    max_loops=2,
)


def main():
    """Main function to run the swarm"""

    # Get task from command line or use default
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        task = "What happens outside of the simulation if we're living in a matrix?"

    result = swarm.run(task=task)
    print(result)


if __name__ == "__main__":
    main()
