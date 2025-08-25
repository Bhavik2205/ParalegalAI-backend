# app/nodes/intent_classifier_node.py (UPDATED - v1.0.6 - Focused on prompt refinement)

from typing import Literal
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser
from app.config import Config
import logging
from langchain_core.messages import BaseMessage # Import BaseMessage for type hinting

logger = logging.getLogger(__name__)

class IntentClassification(BaseModel):
    """Identifies the user's primary intent from their query."""
    intent: Literal["insights", "draft", "update", "review", "compare", "summarize", "unclear", "greeting"] = Field(
        description="The classified intent of the user's request. Must be one of 'insights', 'draft', 'update', 'review', 'compare', 'summarize', 'unclear', or 'greeting'."
    )
    reasoning: str = Field(
        default="", description="Brief explanation for the classified intent."
    )
    # Add a field to capture secondary intent if a greeting is primary but another task is mentioned
    # This will help in scenarios like "Hi, can you review this contract?"
    secondary_intent: Literal["insights", "draft", "update", "review", "compare", "summarize", "unclear", None] = Field(
        default=None, description="Optional: A secondary legal task intent if present alongside a primary greeting."
    )


class IntentClassifierNode:
    """
    A LangGraph node responsible for classifying the user's intent.
    Uses an OpenAI LLM to determine the user's goal based on their query
    or the presence of document content.
    """
    def __init__(self):
        if not Config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
        self.llm = ChatOpenAI(temperature=0, model="gpt-4o", api_key=Config.OPENAI_API_KEY)
        self.parser = JsonOutputParser(pydantic_object=IntentClassification)
        self.prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are an expert legal AI assistant. Your job is to classify the user's primary intent from their message, using these rules:

**Legal Task Intents:**
- 'insights': The user seeks legal explanation, expert opinion, interpretation, or advice. E.g., "Explain the implications of the new data privacy law.", "What are my rights regarding intellectual property?", "Provide a legal opinion on this liability clause.", "Give me insights on contract law."
- 'draft': The user requests creation of a new legal document. E.g., "Draft a Non-Disclosure Agreement for a tech startup.", "Prepare a cease and desist letter.", "Generate a simple will."
- 'update': The user wants to modify or add to an existing legal document. E.g., "Update the termination clause in the previous contract.", "Amend the settlement agreement to include new terms.", "Add a new appendix to the patent application."
- 'review': The user wants a thorough examination of an existing legal document. E.g., "Review this lease agreement for any loopholes.", "Check this brief for legal accuracy.", "Can you identify any missing clauses in this privacy policy?"
- 'compare': The user needs an analysis of similarities/differences between legal documents, laws, or concepts. E.g., "Compare the GDPR and CCPA regulations.", "How does this new bill differ from the previous one?", "Analyze the discrepancies between these two contracts."
- 'summarize': The user requests a concise overview or digest of a legal document or text. E.g., "Summarize the key findings of this court ruling.", "Give me a brief of this contract.", "Condense the main points of the new tax reform."
- 'greeting': The user is simply saying hello, expressing gratitude, or initiating a casual, non-task-oriented conversation *without* a specific legal task being explicitly requested, or if the greeting is the dominant part of the query. E.g., "Hi", "Hello", "How are you?", "Thanks!", "Good morning", "Hey there, how's it going?"
- 'unclear': The user's intent is ambiguous, too broad, or cannot be confidently categorized above. E.g., "Tell me about law.", "What is justice?", "Just checking in."

**Special Handling for Greetings:**
- If the message is *only* a greeting (e.g., "Hi", "Hello", "Thanks", "Good morning"), classify as 'greeting'.
- If the message contains a greeting *and* a clear legal task (e.g., "Hi, can you review this contract?"), classify the legal task as the primary intent and 'greeting' as secondary_intent.
- If the message is a greeting after a previous greeting (consecutive greetings), classify as 'greeting'.
- If the message is a greeting in the middle of a conversation, but no new task is present, classify as 'greeting'.
- If the message is ambiguous or doesn't fit any category, classify as 'unclear'.

**Examples:**
- "Hello" → intent: 'greeting', secondary_intent: null
- "Hi, can you draft an NDA?" → intent: 'draft', secondary_intent: 'greeting'
- "Thanks!" → intent: 'greeting', secondary_intent: null
- "Hi" (after previous greeting) → intent: 'greeting', secondary_intent: null
- "Good morning, please summarize this contract." → intent: 'summarize', secondary_intent: 'greeting'
- "Hi, how are you?" → intent: 'greeting', secondary_intent: null
- "Hi, can you review this contract and summarize it?" → intent: 'review', secondary_intent: 'greeting' (choose the most prominent legal task as primary)
- "Please compare these two contracts." → intent: 'compare', secondary_intent: null

Your output MUST be a JSON object with this schema:
{schema}

Conversation history (for context, but focus on the CURRENT message for primary intent):
{chat_history}
            """,
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{query}"),
    ]
).partial(schema=self.parser.get_format_instructions())
        self.chain = self.prompt | self.llm | self.parser

    def run(self, state: dict) -> dict:
        user_query = state.get("user_query", "").strip() # Added .strip() for robustness
        document_content = state.get("document_content")
        user_query_is_document_content = state.get("user_query_is_document_content", False)
        chat_history: list[BaseMessage] = state.get("chat_history", [])

        query_for_llm = user_query

        # Prioritize document content or user query if it's the main input
        if user_query_is_document_content:
            query_for_llm = f"The user provided content directly. Infer the most likely intent for this content. Content snippet: {user_query[:500]}..."
            logger.info("Initial user_query detected as document content. Classifying intent based on it.")
        elif not user_query and document_content:
            query_for_llm = f"The user uploaded a document. Infer the most likely intent for this document. Document snippet: {document_content[:500]}..."
            logger.info("No explicit query, classifying intent based on document presence.")
        elif not user_query:
            logger.warning("User query not found and no document content for intent classification. Returning 'unclear'.")
            return {
                "intent": "unclear",
                "reasoning": "User query missing and no document content.",
                "final_response": "Please provide a query or upload a document."
            }
        
        logger.info(f"Attempting to classify intent for query: '{query_for_llm[:100]}...'")
        try:
            classification_result = self.chain.invoke({"query": query_for_llm, "chat_history": chat_history})
            intent = classification_result.get("intent", "unclear")
            reasoning = classification_result.get("reasoning", "")
            secondary_intent = classification_result.get("secondary_intent", None) # Capture secondary intent

            # --- MODIFICATION START (How final_response is set in this node) ---
            # The intent classifier node's primary job is classification.
            # It should set a general "processing" message or nothing at all,
            # allowing subsequent nodes to generate the final user-facing response.
            # This avoids the classifier trying to predict the response for all intents.
            response_message = ""
            if intent == "unclear":
                 response_message = f"I'm sorry, I couldn't clearly understand your request: '{user_query}'. {reasoning} Could you please rephrase or provide more details?"
            elif user_query_is_document_content and intent != "unclear":
                # For document-as-query, provide immediate feedback that it's understood.
                response_message = f"You provided content directly. Based on it, your intent has been classified as '{intent}'. {reasoning} Now processing."
            elif not user_query and document_content and intent != "unclear":
                # For document-only upload, provide immediate feedback.
                response_message = f"You uploaded a document. Based on its content, your intent has been classified as '{intent}'. {reasoning} Now processing."
            elif intent == "greeting":
                # Greetings should be handled directly by the greeting node.
                # The classifier sets the intent, the greeting handler will craft the response.
                response_message = "" # Let handle_greeting node create the response
            # For other intents, let downstream nodes (like handle_greeting, perform_review, etc.) set the final_response.
            # This node just sets the intent and possibly an initial acknowledgment.
            # --- MODIFICATION END ---

            logger.info(f"Classified intent: {intent}, Secondary Intent: {secondary_intent}, Reasoning: {reasoning}")
            return {
                "intent": intent,
                "secondary_intent": secondary_intent, # Pass secondary intent
                "final_response": response_message, # This might be empty for non-unclear/doc-only cases. This is fine.
                "error": None
            }
        except Exception as e:
            logger.error(f"Error classifying intent for query '{query_for_llm}': {e}", exc_info=True)
            return {
                "intent": "unclear",
                "reasoning": f"An internal error occurred during classification: {str(e)}",
                "error": str(e),
                "final_response": f"An internal error occurred during intent classification: {str(e)}. Please try rephrasing."
            }