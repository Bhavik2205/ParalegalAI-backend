# agents/update_agent.py

"""
Update Agent
------------
This agent is responsible for modifying existing legal documents
based on user instructions. It ensures the updated document retains
legal integrity and proper formatting.
"""

from typing import Optional, Dict
from core.openrouter_client import generate_response

def update_document(original_text: str, instructions: str) -> str:
    """
    Updates the legal document based on given instructions.

    Args:
        original_text (str): The existing legal document text.
        instructions (str): The user's update instructions.

    Returns:
        str: Updated legal document.
    """
    system_prompt = """
You are an expert legal document editor.
- Modify the given document according to the user's instructions.
- Ensure the update maintains legal integrity, consistency, and formatting.
- Do NOT remove unrelated sections unless explicitly instructed.
- Keep all essential clauses intact unless told otherwise.
"""

    user_prompt = f"""
Original Document:
------------------
{original_text}

Update Instructions:
---------------------
{instructions}

Output the FULL updated legal document.
"""

    return generate_response(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )


def run(user_input: str, session_ctx: Optional[Dict] = None) -> str:
    """
    Handles user request for updating an existing legal document.

    Args:
        user_input (str): The user's update request.
        session_ctx (dict, optional): Session context (should contain original document).

    Returns:
        str: Updated legal document or error message.
    """
    if not session_ctx or "original_document" not in session_ctx:
        return "⚠️ Please provide the original document before requesting an update."

    original_doc = session_ctx["original_document"]
    return update_document(original_doc, user_input)
