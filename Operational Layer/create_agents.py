from swarms.structs.auto_swarm_builder import AutoSwarmBuilder
import re

# Read the profile from the existential output
with open("Existential Layer/output/human_interview_bio.md", "r") as f:
    profile = f.read()

# Extract user name from the profile header
match = re.search(r"# Existential Layer Profile: (.+)", profile)
user_name = match.group(1).strip() if match else "User"

# Initialize to return agent configurations
swarm = AutoSwarmBuilder(
    name=f"Cognitive Function Swarm - {user_name}",
    description="A swarm of agents embodying Jungian cognitive functions tailored to the user's profile",
    execution_type="return-agents",
    model_name="xai/grok-4-fast"  # Using the specified model
)

# Get agent configurations without executing
agent_configs = swarm.run(
    f"Analyze the provided user profile to create agents embodying Jungian cognitive functions. "
    f"For each function, distill the user's unique way of thinking within it—focusing on conceptual thought processes that would be most helpful for supporting their cognitive needs, based on their described architecture, styles, values, principles, and patterns. "
    f"Map to: Te (task/logic organization), Ni (foresight/intuition), Fe (interpersonal/emotional dynamics), Ti (internal logic/analysis), Se (sensory/real-time action), Fi (values/personal ethics), Ne (ideation/novel connections), Si (memory/pattern recall). "
    f"Processing guidance: Synthesize loose, conceptual embodiments from the profile—e.g., for Te, think in terms of structured efficiency that aligns with the user's action-oriented flow; for Fe, focus on empathetic navigation that enhances their relational attunement. Avoid specific examples or tactics; emphasize how the agent's thinking complements the user's meta-cognition. "
    f"Derive roles, tools, and behaviors as flexible supports for the user's thinking, ensuring agents mirror their cognitive flow conceptually. "
    f"Assign names: Maxwell (Te), Sophia (Ni), Clair (Fe), Evelyn (Ti), Serena (Se), Isabella (Fi), Tesla (Ne), Ada (Si). "
    f"Create a swarm where agents think synergistically to replicate the user's overall mental processes. "
    f"Profile: {profile}"
)

print("Generated agents:")
for agent in agent_configs["agents"]:
    print(f"- {agent['agent_name']}: {agent['description']}")
