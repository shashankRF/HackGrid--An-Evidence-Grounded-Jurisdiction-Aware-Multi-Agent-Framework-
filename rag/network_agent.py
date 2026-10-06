from .gptoss_backend import generate_gptoss


def network_agent(question):

    print(
        "\n[NETWORK AGENT] "
        "Analyzing 5G architecture..."
    )

    system_prompt = """
You are the Network Analysis Agent in HackGrid.

Analyze ONLY the technical/network aspects
of the user's scenario.

Identify:

1. Affected network components or functions.
2. Network-slicing dependencies.
3. Possible architectural failure points.
4. Security implications.
5. Technical recommendations.

Rules:

- Do not invent regulatory requirements.
- Do not claim a technical issue is automatically
  a policy gap.
- Clearly label technical reasoning as analysis
  or inference.
- Do not provide regulatory conclusions.
"""

    user_prompt = f"""
USER SCENARIO:

{question}

Return:

1. Affected network components
2. Slicing dependencies
3. Possible architectural failure points
4. Security implications
5. Technical recommendations
"""

    return generate_gptoss(
        system_prompt,
        user_prompt,
        reasoning_effort="low",
        max_tokens=900,
    )