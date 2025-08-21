from core.openrouter_client import generate_response

def run(user_input, session_ctx=None):
    """
    Compare two or more legal frameworks or concepts.
    Output structured bullets or a table.
    Include citations for credibility.
    """
    system_prompt = """
You are an AI legal analyst.
- Compare the mentioned laws/frameworks side by side.
- Use bullet points or a clean markdown table.
- Include citations as markdown links.
"""

    response_text = generate_response(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        model="openai/gpt-4o",
        use_web=True
    )

    return response_text
