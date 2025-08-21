from agents.classifier_agent import classify_intent
from agents.insights_agent import run as insights_agent
from agents.summarize_agent import run as summarize_agent
from agents.compare_agent import run as compare_agent
from agents.greeting_agent import run as greeting_agent
from agents.unclear_agent import run as unclear_agent

def route_query(session_id, user_input):
    classification = classify_intent(user_input)

    response = {
        "session_id": session_id,
        "intent": classification,
        "note": None,
        "output": None
    }

    if not classification.get("legal_related", False):
        response["output"] = "I can only assist with legal topics."
        return response

    if classification.get("unrelated_detected", False):
        response["note"] = "Ignoring unrelated non-legal parts."

    primary_intent = classification.get("primary_intent", "unclear")

    if primary_intent == "insights":
        response["output"] = insights_agent(user_input)
    elif primary_intent == "summarize":
        response["output"] = summarize_agent(user_input)
    elif primary_intent == "compare":
        response["output"] = compare_agent(user_input)
    elif primary_intent == "greeting":
        response["output"] = greeting_agent(user_input)
    else:
        response["output"] = unclear_agent(user_input)

    return response
