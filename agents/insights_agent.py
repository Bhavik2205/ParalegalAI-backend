from core.openrouter_client import generate_response

def run(user_input, session_ctx=None):
    """
    Generate a substantive legal response for the user's query.
    Only legal topics allowed. If non-legal, refuse.
    """

    if not user_input or not isinstance(user_input, str):
        return "Invalid input. Please provide a legal query."

    system_prompt = """
    You are an AI paralegal assistant.
    - Answer ONLY legal-related questions.
    - If the query is unrelated to law, respond: "I can only assist with legal topics."
    - Cite sources using markdown links.
    - Be accurate, concise, and professional.
    """

    # Build messages (with optional session context)
    messages = [{"role": "system", "content": system_prompt}]
    if session_ctx and isinstance(session_ctx, dict) and "history" in session_ctx:
        messages.extend(session_ctx["history"])
    messages.append({"role": "user", "content": user_input})

    try:
        response_text = generate_response(
            messages=messages,
            model="openai/gpt-4o",
            use_web=True
        )
        return response_text.strip() if response_text else "No response generated."
    except Exception as e:
        # In production you’d also log `e`
        return "⚠️ Sorry, I couldn’t process your request right now. Please try again later."
