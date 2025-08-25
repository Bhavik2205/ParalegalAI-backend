# app/graph/workflow.py (UPDATED - v1.0.15 - Fix Recursion on Insights + Doc)

from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from app.nodes.intent_classifier_node import IntentClassifierNode
from app.nodes.legal_review_node import LegalReviewNode
from app.nodes.request_confirmation_node import RequestConfirmationNode
import os
import mimetypes
from pypdf import PdfReader
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from collections import defaultdict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.config import Config
import logging

logger = logging.getLogger(__name__)

# --- Global in-memory session store (NOT FOR PRODUCTION) ---
# Change this to store a dict containing history and document info
session_histories: defaultdict[str, dict] = defaultdict(lambda: {
    "chat_history": [],
    "document_content": None,
    "document_path": None,
    "confirmation_pending_for_review": False,
})
# -----------------------------------------------------------


class WorkflowState(TypedDict):
    """
    Represents the state of our multi-agent legal workflow.
    This state is passed between nodes and updated by them.
    """
    user_query: str
    intent: Literal["insights", "draft", "update", "review", "compare", "summarize", "unclear", "greeting"]
    secondary_intent: Literal["insights", "draft", "update", "review", "compare", "summarize", "unclear", None]
    document_path: str | None
    document_content: str | None
    final_response: str
    error: str | None
    document_was_requested: bool
    user_query_is_document_content: bool
    chat_history: list[BaseMessage]
    confirmation_pending_for_review: bool
    document_was_uploaded_this_turn: bool # <-- NEW STATE VARIABLE


class LegalWorkflow:
    def __init__(self):
        self.intent_classifier_node = IntentClassifierNode()
        self.legal_review_node = LegalReviewNode()
        self.request_confirmation_node = RequestConfirmationNode()

        if not Config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
        self.greeting_llm = ChatOpenAI(temperature=0.7, model="gpt-4o", api_key=Config.OPENAI_API_KEY)
        self.general_response_llm = ChatOpenAI(temperature=0.5, model="gpt-4o", api_key=Config.OPENAI_API_KEY)
        self.app = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(WorkflowState)

        workflow.add_node("classify_intent", self.intent_classifier_node.run)
        workflow.add_node("handle_greeting", self._handle_greeting_response)
        workflow.add_node("perform_review", self.legal_review_node.run)
        workflow.add_node("request_confirmation", self.request_confirmation_node.run)
        workflow.add_node("generate_unclear_response", self._generate_unclear_response)
        workflow.add_node("document_missing_or_error", self._handle_document_missing)
        workflow.add_node("handle_insights", self._handle_insights_response) # NEW: Node for insights
        workflow.add_node("handle_draft", self._handle_draft_response) # NEW: Node for draft

        workflow.set_entry_point("classify_intent")

        workflow.add_conditional_edges(
            "classify_intent",
            self._route_after_intent_classification,
            {
                # These keys must match the string literals returned by _route_after_intent_classification
                "draft": "handle_draft", # Route to a handler node
                "insights": "handle_insights", # Route to a handler node
                "unclear": "generate_unclear_response",
                "greeting": "handle_greeting",
                "review": "perform_review",
                "summarize": "perform_review",
                "update": "perform_review",
                "compare": "perform_review",
                "confirm_review_after_upload": "request_confirmation", # Specific path for document-only uploads / vague queries
                "document_missing_after_intent": "document_missing_or_error", # New path for missing doc
            },
        )

        workflow.add_conditional_edges(
            "request_confirmation",
            self._route_after_confirmation,
            {
                "proceed_with_review": "perform_review",
                "reclassify": "classify_intent", # Reclassify if the user clarifies a different intent
                "cancel_or_unclear": END, # Or route to an "I can't help with that" node
            }
        )

        workflow.add_edge("handle_greeting", END)
        workflow.add_edge("perform_review", END) # The review node generates the final response
        workflow.add_edge("generate_unclear_response", END)
        workflow.add_edge("document_missing_or_error", END)
        workflow.add_edge("handle_insights", END) # End after handling insights
        workflow.add_edge("handle_draft", END) # End after handling draft


        return workflow.compile()

    def _handle_document_missing(self, state: WorkflowState) -> dict:
        error_message = state.get("error", "A required document is missing.")
        user_query = state.get("user_query", "")
        intent = state.get("intent")
        
        response_prompt = ChatPromptTemplate.from_messages([
            ("system",
             """You are a helpful legal AI assistant. You need to inform the user that a document is required to fulfill their request.
             Mention the type of task they are trying to do (e.g., review, summarize) if an intent was identified.
             Politely ask them to upload the document or paste its content.
             Keep it clear and actionable."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", f"User's query: '{user_query}'\nInferred task: '{intent}'\nError: '{error_message}'")
        ])

        try:
            response_chain = response_prompt | self.general_response_llm
            response_message_object = response_chain.invoke({
                "chat_history": state.get("chat_history", []),
                "user_query": user_query,
                "intent": intent,
                "error_message": error_message
            })
            final_message = response_message_object.content
        except Exception as e:
            logger.error(f"Error generating document missing response: {e}", exc_info=True)
            final_message = "I need a document to help with that. Please upload it or paste its content."

        return {
            "final_response": final_message,
            "document_was_requested": True,
            "error": error_message
        }

    def _handle_greeting_response(self, state: WorkflowState) -> dict:
        user_query = state.get("user_query", "")
        chat_history = state.get("chat_history", [])
        secondary_intent = state.get("secondary_intent")

        greeting_prompt = ChatPromptTemplate.from_messages([
            ("system",
             """You are a helpful legal AI assistant. Your task is to generate a friendly and appropriate greeting response.
             Consider the user's current query, the conversation history, and any secondary intent mentioned.

             - If the user is just saying hello, respond kindly.
             - If they are saying hello and also asking for a legal task (secondary intent), acknowledge the greeting AND their task.
             - If it's a continuous greeting (e.g., they said "Hi" again after you responded), respond briefly and acknowledge.
             - Keep responses concise and natural.
             """),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{user_query}")
        ])

        greeting_chain = greeting_prompt | self.greeting_llm

        try:
            response_message_object = greeting_chain.invoke({
                "user_query": user_query,
                "chat_history": chat_history
            })
            response_message = response_message_object.content

            logger.info(f"Generated greeting response: '{response_message}'")
            return {
                "final_response": response_message,
                "error": None
            }
        except Exception as e:
            logger.error(f"Failed to generate dynamic greeting: {e}", exc_info=True)
            return {
                "final_response": "Hello! How can I assist you today?",
                "error": f"Failed to generate dynamic greeting: {str(e)}"
            }

    def _handle_insights_response(self, state: WorkflowState) -> dict:
        user_query = state.get("user_query", "")
        document_content = state.get("document_content")
        chat_history = state.get("chat_history", [])

        prompt_messages = [
            ("system",
             """You are an expert legal AI assistant, providing insights and explanations.
             The user is seeking legal insights, explanation, or advice based on their query.
             If a document is provided, use it as context for your insights.
             Explain legal concepts clearly and provide actionable guidance.
             Do NOT give direct legal advice, but inform them about general legal principles, procedures, or interpretations.
             Always advise them to consult with a qualified legal professional for specific legal counsel.
             
             {document_context}
             """),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{user_query}")
        ]

        document_context = ""
        if document_content:
            document_context = f"The user has provided the following document content for context:\n\n{document_content}\n\n"
        
        insights_prompt = ChatPromptTemplate.from_messages(prompt_messages).partial(document_context=document_context)
        insights_chain = insights_prompt | self.general_response_llm

        try:
            response_message_object = insights_chain.invoke({
                "user_query": user_query,
                "chat_history": chat_history,
            })
            response_message = response_message_object.content
            logger.info(f"Generated insights response.")
            return {
                "final_response": response_message,
                "error": None
            }
        except Exception as e:
            logger.error(f"Failed to generate insights response: {e}", exc_info=True)
            return {
                "final_response": "I apologize, I encountered an issue while generating insights. Please try again or rephrase your request.",
                "error": f"Failed to generate insights: {str(e)}"
            }
            
    def _handle_draft_response(self, state: WorkflowState) -> dict:
        # Placeholder for draft functionality.
        # You'd typically add a sophisticated LLM call here for drafting.
        user_query = state.get("user_query", "")
        document_content = state.get("document_content")
        
        response = f"You asked me to draft something. This feature is under development. Your query was: '{user_query}'."
        if document_content:
            response += "\n\nI also see you provided a document, which could be used for drafting context."
        
        return {
            "final_response": response,
            "error": None
        }

    def _generate_unclear_response(self, state: WorkflowState) -> dict:
        user_query = state.get("user_query", "")
        chat_history = state.get("chat_history", [])

        unclear_prompt = ChatPromptTemplate.from_messages([
            ("system",
             """You are a helpful legal AI assistant. The user's request was unclear or could not be classified into a specific legal task.
             Your goal is to politely state that you didn't understand and ask for clarification or more details.
              **CRITICAL RULE: Do NOT attempt to answer non-legal questions or provide information outside of legal assistance.**
             Instead, gently guide the user back to legal topics.
             Refer to the user's last query and the chat history for context.
             Suggest common tasks you can perform (e.g., reviewing, drafting, summarizing legal documents).
             Keep your response concise and helpful.
             """),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{user_query}")
        ])

        unclear_chain = unclear_prompt | self.general_response_llm

        try:
            response_message_object = unclear_chain.invoke({
                "user_query": user_query,
                "chat_history": chat_history
            })
            response_message = response_message_object.content
            logger.info(f"Generated unclear response: '{response_message}'")
            return {
                "final_response": response_message,
                "error": None,
                "intent": "unclear"
            }
        except Exception as e:
            logger.error(f"Failed to generate unclear response: {e}", exc_info=True)
            return {
                "final_response": "I'm sorry, I couldn't understand your request. Could you please rephrase it or provide more details?",
                "error": f"Failed to generate unclear response: {str(e)}",
                "intent": "unclear"
            }

    
    def _route_after_intent_classification(self, state: WorkflowState) -> Literal[
        "draft", "insights", "unclear", "greeting",
        "review", "summarize", "update", "compare",
        "confirm_review_after_upload", "document_missing_after_intent"
    ]:
        intent = state.get("intent")
        secondary_intent = state.get("secondary_intent")
        document_content = state.get("document_content")
        user_query = state.get("user_query", "").lower().strip() # Ensure query is stripped
        document_was_uploaded_this_turn = state.get("document_was_uploaded_this_turn", False) 
        
        doc_required_intents = ["review", "summarize", "update", "compare"]

        logger.debug(f"Routing: current intent={intent}, secondary_intent={secondary_intent}, document_present={bool(document_content)}, uploaded_this_turn={document_was_uploaded_this_turn}, user_query='{user_query}'")

        # Define phrases that would ONLY trigger a review confirmation if the query is extremely minimal.
        # "this is" should NOT be in this list, as it's often followed by specific context.
        truly_vague_phrases_for_review = ["hi", "hello", "check this", "take a look", "what is this", "i uploaded a document", "hey"]
        
        # Determine if the query is so minimal that it implies *just* "review this document"
        is_minimal_review_query = (
            not user_query or 
            any(phrase == user_query for phrase in truly_vague_phrases_for_review) or # Exact match to a vague phrase
            (user_query.startswith("this is ") and len(user_query.split()) < 4 and "document" in user_query) # e.g., "this is document", "this is my document"
        )
        # For your case "this is payslip how to file case on this company", is_minimal_review_query will be FALSE.

        # --- High-Priority Document Upload Handling ---
        if document_was_uploaded_this_turn:
            # If the classified intent is already a document-specific one (e.g., 'review', 'summarize')
            # OR if the query is specific and leads to a non-document intent (like 'insights', 'draft')
            if intent in doc_required_intents:
                logger.debug(f"Routing (Doc Upload): Classified intent '{intent}' requires document. Proceeding directly.")
                state["confirmation_pending_for_review"] = False
                return intent
            elif intent not in doc_required_intents and not is_minimal_review_query:
                # This covers "insights" + specific query + document upload
                logger.debug(f"Routing (Doc Upload): Classified intent '{intent}' and specific query. Proceeding directly.")
                state["confirmation_pending_for_review"] = False
                return intent
            else: # This is the ONLY path for vague queries with document upload
                logger.debug("Routing (Doc Upload): Query is too minimal/vague with document upload. Requesting review confirmation.")
                state["intent"] = "review" # Force intent to review
                state["confirmation_pending_for_review"] = True
                return "confirm_review_after_upload"
        
        # --- Existing Document Handling (If no new upload this turn) ---
        elif document_content:
            if intent in doc_required_intents:
                logger.debug(f"Routing (Existing Doc): Document present and intent '{intent}' found. Proceeding directly.")
                state["confirmation_pending_for_review"] = False
                return intent
            elif intent == "greeting" and secondary_intent in doc_required_intents:
                 state["intent"] = secondary_intent # Promote secondary intent if doc available
                 logger.debug(f"Routing (Existing Doc): Primary 'greeting', secondary '{secondary_intent}' with doc. Routing to promoted task.")
                 state["confirmation_pending_for_review"] = False 
                 return secondary_intent 
            else:
                # Document is present, but current intent (e.g., insights, draft) doesn't explicitly need it,
                # or it's a greeting without a doc-related secondary intent.
                logger.debug(f"Routing (Existing Doc): Document present, but intent '{intent}' does not directly require it. Following classified intent.")
                state["confirmation_pending_for_review"] = False
                return intent


        # --- No Document or Document Missing Handling ---
        if not document_content and intent in doc_required_intents:
            logger.debug(f"Routing: Intent '{intent}' requires document, but none is present. Routing to document_missing_after_intent.")
            return "document_missing_after_intent"

        # --- General Intent Handling (No document interaction relevant, or document handled) ---
        if intent == "greeting":
            logger.debug("Routing: Pure greeting or greeting without document/draft/insights secondary. Going to handle_greeting.")
            return "greeting" # This catches pure greetings
        elif intent == "draft":
            logger.debug("Routing: Intent 'draft'. Going to handle_draft.")
            state["confirmation_pending_for_review"] = False # Ensure no pending confirmation
            return "draft"
        elif intent == "insights":
            logger.debug("Routing: Intent 'insights'. Going to handle_insights.")
            state["confirmation_pending_for_review"] = False # Ensure no pending confirmation
            return "insights"
        elif intent == "unclear":
            logger.debug("Routing: Unclear intent. Going to generate_unclear_response.")
            return "unclear"
        else:
            logger.warning("Routing: Fallback in _route_after_intent_classification. Should not be reached. Routing to unclear.")
            return "unclear"
    
        
    def _route_after_confirmation(self, state: WorkflowState) -> Literal["proceed_with_review", "reclassify", "cancel_or_unclear"]:
        user_query = state.get("user_query", "").lower()
        original_intent = state.get("intent")
        chat_history = state.get("chat_history", [])

        confirmation_interpretation_prompt = ChatPromptTemplate.from_messages([
            ("system",
             """You are a legal AI assistant. The user was previously asked for confirmation regarding a document task, likely a legal review.
             Your crucial task is to interpret their latest response and determine their intention.
             Output ONLY one of the following exact keywords, without any other text or punctuation, in ALL CAPS:
             - **CONFIRM**: If the user's response clearly indicates agreement to proceed with the *previously suggested task*.
               Examples of CONFIRM: "yes", "yeah", "yep", "proceed", "that's right", "go ahead", "please do", "confirm", "ok", "alright", "yes please", "sure", "absolutely", "you got it", "continue".
             - **RECLASSIFY**: If the user provides a *new, clear legal task* or a clarification that changes the original task (e.g., "summarize it", "no, draft this", "compare with X", "actually, just extract key terms").
             - **CANCEL_OR_UNCLEAR**: If their response is unclear, contradictory, or indicates they want to stop or are unsure (e.g., "no", "stop", "I don't know", "what?", "never mind", "undo", "nah").

             Consider the full conversation history, especially the last question asked.
             Original inferred intent was: {original_intent}.
             The last question asked was a confirmation for a legal review of the document.
             """),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{user_query}")
        ])

        interpretation_chain = confirmation_interpretation_prompt | self.general_response_llm

        try:
            interpretation_result_object = interpretation_chain.invoke({
                "user_query": user_query,
                "original_intent": original_intent,
                "chat_history": chat_history
            })
            interpretation_result = interpretation_result_object.content.strip().upper()

            logger.info(f"Confirmation interpretation: {interpretation_result}")

            if interpretation_result == "CONFIRM":
                logger.info("User confirmed. Proceeding with the original task.")
                state["confirmation_pending_for_review"] = False
                return "proceed_with_review"
            elif interpretation_result == "RECLASSIFY":
                logger.info("User provided a new task. Reclassifying.")
                state["confirmation_pending_for_review"] = False
                return "reclassify"
            else: # Covers CANCEL_OR_UNCLEAR
                logger.info("User did not confirm or provided unclear response. Ending flow.")
                state["confirmation_pending_for_review"] = False
                return "cancel_or_unclear"

        except Exception as e:
            logger.error(f"Failed to interpret confirmation response: {e}", exc_info=True)
            # Fallback logic in case LLM fails
            # Make sure these keywords are comprehensive
            if any(phrase in user_query for phrase in ["yes", "yeah", "yep", "proceed", "go ahead", "please do", "confirm", "ok", "alright", "yes please", "sure", "absolutely", "you got it", "continue"]):
                logger.info("Fallback: User confirmed via keyword. Proceeding with review.")
                state["confirmation_pending_for_review"] = False
                return "proceed_with_review"
            elif any(phrase in user_query for phrase in ["no", "stop", "cancel", "never mind", "undo", "nah", "don't"]):
                logger.info("Fallback: User cancelled via keyword. Ending flow.")
                state["confirmation_pending_for_review"] = False
                return "cancel_or_unclear"
            else:
                logger.info("Fallback: Unclear or reclassify. Reclassifying.")
                state["confirmation_pending_for_review"] = False
                return "reclassify"


    def process_request(self, user_query: str, document_path: str | None = None, initial_document_content: str | None = None, session_id: str = "default_session") -> dict:
        is_user_query_document_content = False
        document_was_uploaded_this_turn = False 
        
        current_document_content = initial_document_content 
        current_document_path = document_path              

        if current_document_path or current_document_content: 
            document_was_uploaded_this_turn = True
            logger.debug(f"Document was uploaded this turn: {document_was_uploaded_this_turn}")

        if not current_document_path and user_query and len(user_query) > 500:
            current_document_content = user_query
            user_query = "User provided content directly." # Standardize this query for classification
            is_user_query_document_content = True
            document_was_uploaded_this_turn = True
            logger.info("Detected potentially long user_query, treating as document content for processing.")

        # Retrieve session data (history, stored document content/path)
        current_session_data = session_histories[session_id]
        current_chat_history = current_session_data["chat_history"]
        
        # If no new document is provided this turn, but one exists in session, use it
        if not document_was_uploaded_this_turn and current_session_data["document_content"]:
            current_document_content = current_session_data["document_content"]
            current_document_path = current_session_data["document_path"]
            logger.debug(f"Using document content from session for session '{session_id}'.")
        
        logger.debug(f"Retrieved chat history for session '{session_id}': {len(current_chat_history)} messages.")

        initial_state: WorkflowState = {
            "user_query": user_query,
            "intent": "unclear", # Will be reclassified
            "secondary_intent": None,
            "document_path": current_document_path,
            "document_content": current_document_content,
            "final_response": "Processing your request...",
            "error": None,
            "document_was_requested": False,
            "user_query_is_document_content": is_user_query_document_content,
            "chat_history": current_chat_history,
            "confirmation_pending_for_review": current_session_data.get("confirmation_pending_for_review", False),
            "document_was_uploaded_this_turn": document_was_uploaded_this_turn
        }

        try:
            # Invoke the graph
            final_state = self.app.invoke(initial_state)

            # Update session history with the latest turn
            session_histories[session_id]["chat_history"].append(HumanMessage(content=user_query))
            if final_state.get("final_response"):
                session_histories[session_id]["chat_history"].append(AIMessage(content=final_state["final_response"]))

            # Crucially, save the document_content and document_path back to the session_histories
            session_histories[session_id]["document_content"] = final_state.get("document_content")
            session_histories[session_id]["document_path"] = final_state.get("document_path")
            session_histories[session_id]["confirmation_pending_for_review"] = final_state.get("confirmation_pending_for_review", False)


            # Clean up document if configured
            # Only delete if it was uploaded THIS turn and we don't need to keep it.
            if final_state.get("document_path") and os.path.exists(final_state["document_path"]) \
               and not Config.KEEP_UPLOADS and document_was_uploaded_this_turn:
                try:
                    os.remove(final_state["document_path"])
                    logger.debug(f"File {final_state['document_path']} deleted as per configuration.")
                except Exception as e:
                    logger.error(f"Error during file cleanup (deletion failed): {e}")
            elif final_state.get("document_path") and Config.KEEP_UPLOADS:
                logger.debug(f"File {final_state['document_path']} kept as per configuration.")

            logger.debug(f"Final state from LangGraph invoke: {final_state}")
            return final_state
        except Exception as e:
            logger.error(f"Unhandled error during workflow processing: {e}", exc_info=True)
            error_response = f"An unexpected error occurred during workflow processing: {str(e)}"
            
            # Ensure history is updated even on error
            session_histories[session_id]["chat_history"].append(HumanMessage(content=user_query))
            session_histories[session_id]["chat_history"].append(AIMessage(content=error_response))

            return {
                "error": str(e),
                "intent": "unclear",
                "user_query": user_query,
                "final_response": error_response,
                "document_was_requested": False,
                "document_path": current_document_path,
                "document_content": current_document_content,
                "chat_history": current_chat_history # Return the history that was used for this turn
            }