# agents/draft_agent.py

"""
Draft Agent
-----------
Responsible for creating legal documents based on user instructions.
Ensures structure, clarity, and professional legal formatting.
"""

from typing import Optional, Dict
from core.openrouter_client import generate_response


# Template Library
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
    """
    template = TEMPLATE_LIBRARY.get(doc_type.lower())
    if not template:
        return f"⚠️ Sorry, I don’t have a template for '{doc_type}'. Please specify details."

    try:
        return template.format(**context)
    except KeyError as e:
        missing_field = str(e).strip("'")
        return f"⚠️ Missing required field: {missing_field}. Please provide it."

def extract_doc_type(user_input: str) -> Optional[str]:
    """
    Extracts the type of legal document from user input.
    """
    user_input = user_input.lower()
    if "nda" in user_input:
        return "nda"
    elif "contract" in user_input:
        return "contract"
    return None


def run(user_input: str, session_ctx: Optional[Dict] = None) -> str:
    """
    Handles user request for drafting a new legal document.
    """
    doc_type = extract_doc_type(user_input)

    if not doc_type:
        return "⚠️ Please specify the type of legal document you want me to draft (e.g., NDA, contract)."

    # Default placeholders for required fields
    default_context = {
        "nda": {
            "date": "____",
            "party_a": "____",
            "party_b": "____",
            "term": "____"
        },
        "contract": {
            "date": "____",
            "party_a": "____",
            "party_b": "____",
            "scope_of_work": "____",
            "payment_terms": "____",
            "start_date": "____",
            "end_date": "____",
            "jurisdiction": "____"
        }
    }

    # Use existing session context if provided
    context = session_ctx or default_context[doc_type]

    draft = generate_document(doc_type, context)

    # If missing fields, generate a helpful AI response asking user
    if "⚠️ Missing required field" in draft:
        missing_field = draft.split(":")[-1].strip(". Please provide it.")
        ai_message = generate_response([
            {"role": "system", "content": "You are a legal assistant helping fill missing fields."},
            {"role": "user", "content": f"The user needs to provide the missing field '{missing_field}' for the {doc_type}."}
        ])
        return draft + "\n\n" + ai_message

    return draft
