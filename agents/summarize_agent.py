from core.openrouter_client import generate_response

def run(user_input, session_ctx=None):
    """
    Summarize provided legal text.
    If text is large or external, allow :online only if needed.
    """
    system_prompt = """
You are an AI legal summarizer.
- Summarize legal text concisely in plain language.
- Focus on key obligations, rights, or penalties.
"""

    response_text = generate_response(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        model="openai/gpt-4o",
        use_web=False  # Summary usually does not require online lookup
    )

    return response_text
