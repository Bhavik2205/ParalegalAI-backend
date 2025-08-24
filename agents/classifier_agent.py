# agents/classifier_agent.py
import json
from core.openrouter_client import generate_response

def classify_intent(user_input, case_context=None):
    """
    Classify user input into primary and secondary legal intents,
    detect unrelated content, and check case relevance.

    Args:
        user_input (str): The user query.
        case_context (str): Optional description of current case/session.

    Returns:
        dict: {
            "primary_intent": str,
            "secondary_intent": str or None,
            "legal_related": bool,
            "unrelated_detected": bool,
            "case_relevance": "same" | "new" | "unclear"
        }
    """

    system_prompt = f"""
You are an expert AI legal assistant. Your job is to classify the user's query into these intents:

- insights: legal explanation, expert opinion, interpretation, or advice
- draft: creation of a new legal document
- update: modification of an existing document
- review: thorough examination of an existing document
- compare: analysis of similarities/differences
- summarize: concise overview of a document or text
- greeting: user is greeting or thanking
- unclear: intent is ambiguous or outside these categories

### Value-added intents:
- citations: retrieve or reference case laws, statutes, or precedents
- compliance: check compliance of a document or scenario with laws/regulations
- translate: translate legal text between languages
- explain_terms: explain legal terms or jargon in plain language
- history: retrieve or summarize past queries/documents in this session
- clarify: when the user asks what the system can do or how it works


### Additional Task:
Determine CASE RELEVANCE based on current session context:
- "same": clearly related to the ongoing case/session
- "new": clearly about a different case, document, or topic
- "unclear": cannot confidently determine

### Important:
- legal_related = true if at least part of the query involves law
- unrelated_detected = true if ANY part of the query is non-legal
- If fully unrelated, primary_intent = "unclear", legal_related = false

### Rules:
1. Respond ONLY in JSON format
2. Use exactly these keys:
   primary_intent, secondary_intent, legal_related, unrelated_detected, case_relevance
3. secondary_intent = null if none

### Additional Rules:
- If the query has both legal and unrelated parts, classify the legal part normally, 
  but set unrelated_detected = true.
- If the query is entirely unrelated, primary_intent = "unclear", legal_related = false.

Example:
{{
    "primary_intent": "review",
    "secondary_intent": "summarize",
    "legal_related": true,
    "unrelated_detected": false,
    "case_relevance": "same"
}}
"""

    if case_context:
        user_prompt = f"Current case context: {case_context}\n\nClassify this query: {user_input}"
    else:
        user_prompt = f"Classify this query: {user_input}"

    response_text = generate_response(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        model="openai/gpt-4o-mini",
        use_web=False
    )

    # Retry logic if JSON is broken
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        retry_text = generate_response(
            messages=[
                {"role": "system", "content": "Fix this into valid JSON strictly."},
                {"role": "user", "content": response_text}
            ],
            model="openai/gpt-4o-mini",
            use_web=False
        )
        try:
            return json.loads(retry_text)
        except json.JSONDecodeError:
            return {
                "primary_intent": "unclear",
                "secondary_intent": None,
                "legal_related": False,
                "unrelated_detected": False,
                "case_relevance": "unclear"
            }
