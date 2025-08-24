# agents/draft_agent.py

"""
Draft Agent
-----------
This agent is responsible for creating new legal documents 
based on user instructions. It ensures structure, clarity, 
and professional legal formatting. 
"""

from typing import Optional, Dict


TEMPLATE_LIBRARY = {
    "nda": """
NON-DISCLOSURE AGREEMENT (NDA)

This Non-Disclosure Agreement ("Agreement") is entered into on {date} 
between {party_a} and {party_b}.

1. Purpose: The parties wish to explore a potential business relationship 
   and agree to protect confidential information.

2. Definition of Confidential Information:
   "Confidential Information" means any non-public, proprietary, or 
   sensitive information disclosed.

3. Obligations:
   The receiving party agrees not to disclose, copy, or misuse 
   Confidential Information.

4. Term:
   This Agreement remains in effect for {term} years.

Signed:

_______________________          _______________________
{party_a}                        {party_b}
    """,

    "contract": """
LEGAL CONTRACT AGREEMENT

This Contract is made on {date} between {party_a} ("First Party") 
and {party_b} ("Second Party").

1. Scope of Work:
   {scope_of_work}

2. Payment Terms:
   {payment_terms}

3. Duration:
   The contract shall commence on {start_date} and end on {end_date}.

4. Governing Law:
   This agreement shall be governed by the laws of {jurisdiction}.

Signed:

_______________________          _______________________
{party_a}                        {party_b}
    """,
}


def generate_document(doc_type: str, context: Dict[str, str]) -> str:
    """
    Generates a legal draft based on doc_type and provided context.

    Args:
        doc_type (str): The type of document (e.g., "nda", "contract").
        context (dict): Key-value pairs to fill placeholders.

    Returns:
        str: Drafted legal document.
    """
    template = TEMPLATE_LIBRARY.get(doc_type.lower())
    if not template:
        return f"⚠️ Sorry, I don’t have a template for '{doc_type}'. Please specify details."

    try:
        return template.format(**context)
    except KeyError as e:
        missing_field = str(e).strip("'")
        return f"⚠️ Missing required field: {missing_field}. Please provide it."


def run(user_input: str, session_ctx: Optional[Dict] = None) -> str:
    """
    Handles user request for drafting a new legal document.

    Args:
        user_input (str): The user’s drafting request.
        session_ctx (dict, optional): Session context for continuity.

    Returns:
        str: Drafted legal document or clarification message.
    """
    # Very basic keyword detection for doc type
    if "nda" in user_input.lower():
        return generate_document("nda", {
            "date": "____",
            "party_a": "____",
            "party_b": "____",
            "term": "___"
        })

    elif "contract" in user_input.lower():
        return generate_document("contract", {
            "date": "____",
            "party_a": "____",
            "party_b": "____",
            "scope_of_work": "____",
            "payment_terms": "____",
            "start_date": "____",
            "end_date": "____",
            "jurisdiction": "____"
        })

    else:
        return "⚠️ Please specify the type of legal document you want me to draft (e.g., NDA, contract)."
