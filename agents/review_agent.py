# agents/review_agent.py
from core.openrouter_client import generate_response

def run(user_input, session_ctx=None):
    """
    Review an existing legal document or text.
    Provide structured feedback on:
    - Clarity of language
    - Legal enforceability
    - Risks and liabilities
    - Compliance with common standards
    - Suggested improvements
    """

    system_prompt = """
You are an AI legal document reviewer.
- Carefully examine the provided legal document or text.
- Identify strengths and weaknesses in language, structure, and enforceability.
- Highlight risks, ambiguities, or missing clauses.
- Suggest practical improvements to strengthen the document.
- Be concise, professional, and structured in your feedback.
- Do NOT draft an entirely new document—focus on review only.
"""

    response_text = generate_response(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        model="openai/gpt-4o",
        use_web=False  # review usually doesn’t need external lookup
    )

    return response_text
