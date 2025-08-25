# app/nodes/request_confirmation_node.py
import logging

logger = logging.getLogger(__name__)

class RequestConfirmationNode:
    """
    A LangGraph node responsible for asking the user for confirmation
    before proceeding with a document review.
    """
    def run(self, state: dict) -> dict:
        document_type = "document"
        document_content_snippet = state.get("document_content", "")

        # Attempt to infer document type for a more specific message
        if document_content_snippet:
            lower_content = document_content_snippet.lower()
            if "payslip" in lower_content:
                document_type = "payslip"
            elif "agreement" in lower_content or "contract" in lower_content or "nda" in lower_content:
                document_type = "legal agreement"
            elif "report" in lower_content or "policy" in lower_content:
                document_type = "document" # General fallback

        response = (
            f"I've detected you've uploaded a {document_type} and it looks like you want me to perform a review. "
            "Is that correct? Please type 'yes' to proceed with the review, or provide a different request."
        )
        logger.info(f"Requesting confirmation for review: {response}")

        return {
            "final_response": response,
            "confirmation_pending_for_review": True, # Set flag in state
            "error": None
        }