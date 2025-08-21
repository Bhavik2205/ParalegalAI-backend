from core.openrouter_client import generate_response
import json

def classify_intent(user_input):
    """
    Classify user input into primary and secondary legal intents.
    Detect unrelated content as well.

    Returns:
        dict: {
            "primary_intent": str,
            "secondary_intent": str or None,
            "legal_related": bool,
            "unrelated_detected": bool
        }
    """

    system_prompt = """
You are an expert AI legal assistant. Your job is to analyze the user's query and classify it into these intents:

- insights: The user seeks legal explanation, expert opinion, interpretation, or advice.
- draft: The user requests creation of a new legal document.
- update: The user wants to modify or add to an existing legal document.
- review: The user wants a thorough examination of an existing legal document.
- compare: The user needs an analysis of similarities/differences between legal documents, laws, or concepts.
- summarize: The user requests a concise overview or digest of a legal document or text.
- greeting: The user is simply greeting or expressing gratitude without a legal task.
- unclear: The user's intent is ambiguous or doesn't fit the above categories.

### IMPORTANT:
- You must detect if the query is fully or partially legal-related.
- If any part of the query is unrelated to law (e.g., coding, math, personal chit-chat), set "unrelated_detected" to true.
- If the entire query is unrelated to law, set primary intent to "unclear" and legal_related = false.

### Rules:
1. Respond ONLY in JSON format.
2. primary_intent = main legal intent OR "unclear" if none.
3. secondary_intent = another legal intent if strongly implied, else null.
4. legal_related = true if at least part of the query is legal.
5. unrelated_detected = true if any part of the query is unrelated.

Example:
{
    "primary_intent": "insights",
    "secondary_intent": null,
    "legal_related": true,
    "unrelated_detected": true
}
"""

    user_prompt = f"Classify this query: {user_input}"

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
            "primary_intent": "unclear",
            "secondary_intent": None,
            "legal_related": False,
            "unrelated_detected": False
        }
