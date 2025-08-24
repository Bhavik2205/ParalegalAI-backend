def run(user_input, session_ctx=None):
    """
    Fallback agent for unclear or non-legal queries.
    """
    # Optional: you could log the input here for monitoring
    # log_unhandled_query(user_input)

    return {
        "message": "I couldn’t understand that. Could you please rephrase your legal question?"
    }
