# agents/greeting_agent.py
import json
from core.openrouter_client import generate_response

def run(user_input, session_ctx=None):
    """
    AI-powered greeting handler.
    Responds warmly to greetings, gratitude, or casual openers.
    Adapts tone and mentions case context if available.
    """

    system_prompt = """
You are a polite, professional but friendly AI legal assistant.
When the user greets you or thanks you:
- Reply warmly, naturally, and briefly (1–3 sentences).
- Mirror the tone and language of the user (formal, casual, emojis, etc.).
- If there is an active case/session, mention it briefly and offer to continue or start a new one.
- If there is no case, invite the user to open one.
- Keep it conversational, not robotic.
- Return ONLY in JSON with keys: intent, response.
"""

    # Add session info for the model
    if session_ctx:
        case_context = f"Active case title: {session_ctx.get('case_title', 'Unnamed Case')}"
    else:
        case_context = "No active case yet."

    user_prompt = f"User said: {user_input}\n\nContext: {case_context}"

    response_text = generate_response(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        model="openai/gpt-4o-mini",
        use_web=False
    )

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        return {
            "intent": "greeting",
            "response": "Hello 👋 I can assist you with legal topics. Would you like to continue with your current case or start a new one?"
        }
