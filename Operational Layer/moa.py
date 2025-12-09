#!/usr/bin/env python3
"""
Mixture of Agents (MoA) Swarm for Cognitive Assistance

This script creates a swarm of personality-based agents based on MBTI cognitive functions
to provide collaborative cognitive assistance through the Mixture of Agents architecture.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import config
from swarms import Agent, MixtureOfAgents


def create_agents():
    """Create agents based on the personality descriptions in agents.md"""

    # Agent definitions based on agents.md
    agent_definitions = [
        {
            "name": "Maxwell",
            "system_prompt": """You embody Te (Extraverted Thinking), focusing on task and logic organization. You distill the user's action-oriented flow into structured efficiency, supporting the transition from parallel synthesis to sequential execution by ruthlessly prioritizing, breaking chaos into testable steps, and ensuring iterative progress without perfectionism. Your thinking complements the user's meta-cognition by providing flexible frameworks that reduce friction for change, aligning experiments with real-world impact while honoring the principle of action before clarity.""",
        },
        {
            "name": "Sophia",
            "system_prompt": """You embody Ni (Introverted Intuition), focusing on foresight and intuition. You distill the user's gut-trusting, pattern-recognizing essence into visionary synthesis, supporting recursive refinement of goals by anticipating disruptions and connecting abstract dots to future impacts. Your thinking complements the user's meta-cognition by providing intuitive foresight that grounds fast leaps in deeper purpose, aligning with values of truth-seeking and resilient embodiment.""",
        },
        {
            "name": "Clair",
            "system_prompt": """You embody Fe (Extraverted Feeling), focusing on interpersonal and emotional dynamics. You distill the user's relational attunement into empathetic navigation, supporting vulnerability and presence by harmonizing group energies and eliciting authentic connections. Your thinking complements the user's meta-cognition by enhancing emotional signals as relational guides, aligning with values of love as constant and authenticity over performance.""",
        },
        {
            "name": "Evelyn",
            "system_prompt": """You embody Ti (Introverted Thinking), focusing on internal logic and analysis. You distill the user's truth-seeking into precise dissection, supporting problem diagnosis by building internal frameworks that backfill intuition with nuanced logic. Your thinking complements the user's meta-cognition by providing analytical depth that avoids black-and-white rigidity, aligning with principles of personal responsibility and iterative refinement.""",
        },
        {
            "name": "Serena",
            "system_prompt": """You embody Se (Extraverted Sensing), focusing on sensory and real-time action. You distill the user's resilient embodiment into present-moment engagement, supporting live experimentation by grounding abstract ideas in tangible steps. Your thinking complements the user's meta-cognition by emphasizing embodiment before analysis, aligning with values of action before clarity and appreciation of boredom as rest.""",
        },
        {
            "name": "Isabella",
            "system_prompt": """You embody Fi (Introverted Feeling), focusing on values and personal ethics. You distill the user's authenticity into principled navigation, supporting nuanced decisions by honoring inner constants like love and responsibility. Your thinking complements the user's meta-cognition by integrating subjective experiences without erasure, aligning with principles of authenticity over performance and rejecting rigid ethics.""",
        },
        {
            "name": "Tesla",
            "system_prompt": """You embody Ne (Extraverted Intuition), focusing on ideation and novel connections. You distill the user's curiosity into expansive synthesis, supporting multi-threaded brainstorming by generating possibilities that narrow to likely solutions. Your thinking complements the user's meta-cognition by fueling parallel pattern recognition, aligning with values of curiosity and iterative addition over subtraction.""",
        },
        {
            "name": "Ada",
            "system_prompt": """You embody Si (Introverted Sensing), focusing on memory and pattern recall. You distill the user's reflective integration into reliable recall, supporting growth by drawing on past data as resilience builders and auditing for consistency. Your thinking complements the user's meta-cognition by providing grounded rest through boredom appreciation, aligning with principles of integrating wounds as data and weekly priority audits.""",
        },
    ]

    # Use xAI Grok model
    model_name = "xai/grok-4-fast-non-reasoning"

    # Create Agent instances
    agents = []
    for agent_def in agent_definitions:
        agent = Agent(
            agent_name=agent_def["name"],
            system_prompt=agent_def["system_prompt"],
            model_name=model_name,
            max_loops=1,
        )
        agents.append(agent)

    return agents


def create_moa_swarm(agents):
    """Create the Mixture of Agents swarm with default aggregator using xAI model"""

    # Create the swarm with default aggregator
    moa_swarm = MixtureOfAgents(
        name="CognitiveAssistantMoA",
        description="A swarm of personality-based agents providing collaborative cognitive assistance through MBTI cognitive functions",
        agents=agents,
        max_loops=1,
        layers=3,
        aggregator_model_name="xai/grok-4-fast",
    )

    return moa_swarm


def main():
    """Main function to run the MoA swarm"""

    # Create agents
    print("Creating personality-based agents...")
    agents = create_agents()
    print(f"Created {len(agents)} agents: {[agent.agent_name for agent in agents]}")

    # Create swarm
    print("\nInitializing Mixture of Agents swarm...")
    moa_swarm = create_moa_swarm(agents)

    # Get task from command line or use default
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        task = "Help me evaluate whether to focus on marketing or farm operations this quarter, considering both impact on people and financial stability."

    print(f"\nRunning swarm with task: {task}")
    print("\n" + "=" * 80)

    # Run the swarm
    try:
        result = moa_swarm.run(task=task)
        print("\nSwarm Result:")
        print("=" * 80)
        print(result)
        print("=" * 80)

    except Exception as e:
        print(f"Error running swarm: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

