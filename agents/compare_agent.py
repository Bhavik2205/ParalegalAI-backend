# agents/compare_agent.py
from core.openrouter_client import generate_response
import json

def run(user_input, session_ctx=None):
    """
    Compare two or more legal frameworks, laws, or concepts.
    Returns structured comparison with bullets or markdown table and citations.
    """

    system_prompt = """
You are an AI legal analyst.

TASK:
- Compare the mentioned laws/frameworks/concepts side by side.
- Choose one of two formats:
  1. bullets (clear points of comparison)
  2. table (markdown table with columns for each law/concept)
- Every bullet or table row must include a markdown citation with a valid URL.
- Keep the tone factual, concise, and professional.

OUTPUT JSON:
{
  "format": "bullets" | "table",
  "comparison": "markdown content with bullets or table"
}
"""

    # If we have session context, include it
    user_prompt = f"Context: {session_ctx}\n\nCompare: {user_input}" if session_ctx else f"Compare: {user_input}"

    response_text = generate_response(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        model="openai/gpt-4o",
        use_web=True
    )

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # fallback
        return {
            "format": "bullets",
            "comparison": f"- Unable to produce structured comparison for: {user_input}\n"
                          f"- Please try rephrasing your request."
        }
