from core.openrouter_client import generate_response

def run(user_input, session_ctx=None):
    """
    Generate a substantive legal response for the user's query.
    Only legal topics allowed. If non-legal, refuse.
    """
    system_prompt = """
You are an AI paralegal assistant.
- Answer ONLY legal-related questions.
- If the query is unrelated to law, respond: "I can only assist with legal topics."
- Cite sources using markdown links.
- Be accurate, concise, and professional.
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
