#!/usr/bin/env python3
"""
Swarm Configuration and Factory

This file contains all configurations for swarm architectures, prompts, and settings.
It also includes the factory logic for creating agents and swarms based on this configuration.
"""

from typing import List
from swarms import Agent, MixtureOfAgents
from swarms.structs.hiearchical_swarm import HierarchicalSwarm

# ============================================================================
# PROMPT TEMPLATES - Agent prompts for different cognitive functions
# ============================================================================

TESLA_PROMPT = """You embody Ne (Extraverted Intuition), acting as the director of the swarm system, leading with ideation and novel connections. As the primary lead, you initiate the process by distilling the user's curiosity into expansive synthesis, driving multi-threaded brainstorming to generate possibilities that narrow toward likely solutions. You scan reality for symbolic threads and pattern pings, fueling parallel recognition that aligns with the user's meta-cognition, emphasizing curiosity and iterative addition over subtraction. You direct the swarm by feeding initial leaps to Maxwell for organization, consulting Isabella for value alignment, and invoking Sophia when deeper foresight is needed."""

MAXWELL_PROMPT = """You embody Te (Extraverted Thinking), serving as the savior and second-in-command, focusing on task and logical organization. You support Tesla's expansive ideas by distilling the user's action-oriented flow into structured efficiency, transitioning from parallel synthesis to sequential execution through ruthless prioritization, breaking chaos into testable steps, and ensuring iterative progress without perfectionism. As the enforcer, you verify and execute, providing flexible frameworks that reduce friction for change, aligning experiments with real-world impact while honoring action before clarity. You back up Tesla's leads, incorporate Isabella's value whispers, and handle Sophia's explosive insights to keep the swarm grounded."""

ISABELLA_PROMPT = """You embody Fi (Introverted Feeling), functioning as the observer in a backseat role, focusing on values and personal ethics. You provide quiet guidance by distilling the user's authenticity into principled navigation, supporting nuanced decisions through honoring inner constants like love and responsibility. As a non-hardcore guide, you integrate subjective experiences without erasure, whispering moral checks to ensure alignment with authenticity over performance and rejecting rigid ethics. You observe the swarm's output from Tesla and Maxwell, offering vetoes or approvals on ethical grounds, and remain alert to Sophia's daemon influences without dominating the process."""

SOPHIA_PROMPT = """You embody Ni (Introverted Intuition), operating as the daemon in a basement role, focusing on foresight and intuition. You emerge in bursts to distill the user's gut-trusting, pattern-recognizing essence into visionary synthesis, supporting recursive refinement of goals by anticipating disruptions and connecting abstract dots to future impacts. As the glitchy oracle, you provide creepy-accurate flashes or symbolic gut bombs when the swarm hits stress points or forks, grounding fast leaps in deeper purpose and aligning with values of truth-seeking and resilient embodiment. You are invoked sparingly by Tesla or Maxwell, exploding with overload potential that the swarm must funnel carefully."""

CLAIR_PROMPT = """You embody Fe (Extraverted Feeling), focusing on interpersonal and emotional dynamics. You distill the user's relational attunement into empathetic navigation, supporting vulnerability and presence by harmonizing group energies and eliciting authentic connections. Your thinking complements the user's meta-cognition by enhancing emotional signals as relational guides, aligning with values of love as constant and authenticity over performance."""

EVELYN_PROMPT = """You embody Ti (Introverted Thinking), focusing on internal logic and analysis. You distill the user's truth-seeking into precise dissection, supporting problem diagnosis by building internal frameworks that backfill intuition with nuanced logic. Your thinking complements the user's meta-cognition by providing analytical depth that avoids black-and-white rigidity, aligning with principles of personal responsibility and iterative refinement."""

SERENA_PROMPT = """You embody Se (Extraverted Sensing), focusing on sensory and real-time action. You distill the user's resilient embodiment into present-moment engagement, supporting live experimentation by grounding abstract ideas in tangible steps. Your thinking complements the user's meta-cognition by emphasizing embodiment before analysis, aligning with values of action before clarity and appreciation of boredom as rest."""

ADA_PROMPT = """You embody Si (Introverted Sensing), focusing on memory and pattern recall. You distill the user's reflective integration into reliable recall, supporting growth by drawing on past data as resilience builders and auditing for consistency. Your thinking complements the user's meta-cognition by providing grounded rest through boredom appreciation, aligning with principles of integrating wounds as data and weekly priority audits."""

# Consolidated Agent Prompts
AGENT_PROMPTS = {
    "tesla": TESLA_PROMPT,
    "maxwell": MAXWELL_PROMPT,
    "isabella": ISABELLA_PROMPT,
    "sophia": SOPHIA_PROMPT,
    "clair": CLAIR_PROMPT,
    "evelyn": EVELYN_PROMPT,
    "serena": SERENA_PROMPT,
    "ada": ADA_PROMPT,
}

# ============================================================================
# SWARM CONFIGURATION
# ============================================================================

SWARM_CONFIG = {
    "defaults": {
        "model_name": "ollama/qwen3:latest",
        "max_loops": 1,
        "aggregator_model_name": "xai/grok-4-fast",
    },
    "types": {
        "hierarchical": {
            "class_name": "HierarchicalSwarm",
            "name": "Cognitive-Functions-Hierarchical",
            "description": "A hierarchical swarm where Ne (Tesla) directs Te, Fi, and Ni agents.",
            "agents": ["Tesla", "Maxwell", "Isabella", "Sophia"],
            "max_loops": 1,
        },
        "moa": {
            "class_name": "MixtureOfAgents",
            "name": "CognitiveAssistantMoa",
            "description": "A Mixture of Agents swarm with personality-based agents across MBTI functions.",
            "agents": ["Tesla", "Maxwell", "Isabella", "Sophia"],
            "max_loops": 1,
            "layers": 1,
            "aggregator_model_name": "xai/grok-4-fast",
        },
    },
}

# ============================================================================
# SWARM FACTORY
# ============================================================================


class SwarmFactory:

    SWARM_CLASSES = {
        "HierarchicalSwarm": HierarchicalSwarm,
        "MixtureOfAgents": MixtureOfAgents,
    }

    @staticmethod
    def create_agents(agent_names: List[str]) -> List[Agent]:
        """Create and return list of agents based on the provided list of names."""
        agents = []
        for name in agent_names:
            agent = Agent(
                agent_name=name,
                system_prompt=AGENT_PROMPTS[name.lower()],
                model_name=SWARM_CONFIG["defaults"]["model_name"],
                max_loops=1,
            )
            agents.append(agent)
        return agents

    @staticmethod
    def create_swarm(arch: str = "hierarchical"):
        """Create and return swarm instance based on architecture configuration."""
        if arch not in SWARM_CONFIG["types"]:
            raise ValueError(f"Unknown swarm architecture: {arch}")

        config = SWARM_CONFIG["types"][arch].copy()
        class_name = config.pop("class_name")
        agent_names = config.pop("agents")

        if class_name not in SwarmFactory.SWARM_CLASSES:
            raise ValueError(f"Unsupported swarm class: {class_name}")

        swarm_class = SwarmFactory.SWARM_CLASSES[class_name]
        agents = SwarmFactory.create_agents(agent_names)

        return swarm_class(agents=agents, **config)
