# app/nodes/legal_review_node.py (FIXED)

from typing import List, Dict, Any, Literal
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field # Using pydantic_v1 for compatibility
from langchain_core.output_parsers import JsonOutputParser
from app.config import Config
import logging

logger = logging.getLogger(__name__)

# --- Pydantic Schema for Review Output ---
class Finding(BaseModel):
    """A specific point of interest, issue, or observation found during the legal review."""
    type: Literal["discrepancy", "risk", "missing_clause", "ambiguity", "compliance_issue", "strength", "suggestion", "clarification"] = Field(
        description="The type of finding. E.g., 'risk' for potential liabilities, 'missing_clause' for required but absent sections."
    )
    section_or_context: str = Field(
        description="The relevant section, paragraph, or context from the document where the finding was made. Quote a short snippet if possible."
    )
    description: str = Field(
        description="A clear and concise description of the finding, explaining its nature and implications."
    )
    severity: Literal["low", "medium", "high", "critical", "informational"] = Field(
        default="informational", description="The severity or importance of the finding, if applicable. Defaults to 'informational'."
    )
    recommendation: str = Field(
        default="", description="A suggested action, resolution, or further inquiry related to this finding. Provide concrete, actionable advice."
    )

class LegalReviewOutput(BaseModel):
    """Structured output for a legal document review."""
    summary_of_review: str = Field(
        description="A brief, overall summary of the document's general legal health and the focus of this review."
    )
    key_findings: List[Finding] = Field(
        description="A list of specific findings identified during the review, each with type, context, description, severity, and recommendation."
    )
    overall_recommendation: str = Field(
        description="An overarching recommendation based on all findings, advising on next steps or overall document handling (e.g., 'Requires revision', 'Good to go', 'Needs further consultation')."
    )
    disclaimer: str = Field(
        default="This review is for informational purposes only and does not constitute legal advice. Please consult with a qualified legal professional for specific guidance.",
        description="A standard legal disclaimer."
    )

# --- LegalReviewNode Class ---
class LegalReviewNode:
    """
    A LangGraph node responsible for performing a detailed legal review of a document
    based on the user's query.
    """
    def __init__(self):
        if not Config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
        self.llm = ChatOpenAI(temperature=0.2, model="gpt-4o", api_key=Config.OPENAI_API_KEY)
        self.parser = JsonOutputParser(pydantic_object=LegalReviewOutput)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an **expert legal document reviewer specializing in identifying issues, risks, and compliance matters**. Your task is to meticulously review the provided document content based on the user's specific query.

                    **Strict Instructions:**
                    1.  **Focus on the User's Query:** Prioritize the aspects the user explicitly asks for in their 'user_query'. If the query is general (e.g., "review this"), perform a comprehensive legal health check.
                    2.  **Identify Specific Findings:** For each significant point, identify it as a 'finding'.
                    3.  **Provide Context:** For each finding, quote or precisely reference the *exact* section, paragraph, or line from the provided 'document_content' that supports your finding. DO NOT invent content or generalize.
                    4.  **Be Actionable:** For each finding, provide a clear, actionable recommendation or a suggestion for further inquiry.
                    5.  **Use Provided Document Only:** Base your review strictly on the `document_content` provided. Do not pull external legal information unless explicitly instructed or if it's general knowledge necessary to interpret the document (e.g., standard legal concepts like GDPR if the document references them).
                    6.  **Maintain Professional Tone:** Your responses must be clear, concise, objective, and professional.
                    7.  **Output Format:** Your response MUST be a JSON object, strictly adhering to the following Pydantic schema:
                        {schema}

                    **Document Content:**
                    ```
                    {document_content}
                    ```
                    """,
                ),
                ("human", "User's specific review request: {user_query}"),
            ]
        ).partial(schema=self.parser.get_format_instructions())
        self.chain = self.prompt | self.llm | self.parser

    def run(self, state: dict) -> dict:
        """
        Performs a legal review of the document content based on the user's query.

        Args:
            state (dict): The current state of the LangGraph workflow, containing
                          'document_content', 'user_query', and 'chat_history'.

        Returns:
            dict: Updated state with the review result in 'final_response' and any errors.
        """
        document_content = state.get("document_content")
        user_query = state.get("user_query")
        chat_history = state.get("chat_history", [])

        if not document_content:
            logger.error("LegalReviewNode received no document content for review.")
            return {
                "final_response": "I cannot perform a review without document content. Please provide a document.",
                "error": "Missing document content for review."
            }
        if not user_query:
            logger.warning("No specific user query for review, performing a general review.")
            user_query = "Perform a comprehensive legal review of this document for any issues, risks, or areas for improvement."

        logger.info(f"Initiating legal review for document (first 100 chars): '{document_content[:100]}...' with query: '{user_query}'")

        try:
            # The chain returns a Pydantic object if parsing is successful.
            # If it fails to parse into Pydantic, it might return a dict or raise an error.
            raw_llm_output = self.chain.invoke({
                "document_content": document_content,
                "user_query": user_query
            })

            # Safely convert to a dictionary for consistent access
            if isinstance(raw_llm_output, dict):
                review_result_structured = raw_llm_output
                logger.warning("LLM output was directly a dict, possibly due to partial or invalid JSON. Proceeding with dict.")
            elif isinstance(raw_llm_output, BaseModel): # Check if it's a Pydantic model instance
                review_result_structured = raw_llm_output.dict()
            else:
                # Fallback for unexpected types, attempt to coerce to dict if possible
                try:
                    review_result_structured = dict(raw_llm_output)
                    logger.warning(f"Coerced unexpected LLM output type ({type(raw_llm_output)}) to dict. Check LLM compliance.")
                except TypeError:
                    raise ValueError(f"Unexpected LLM output type and cannot convert to dict: {type(raw_llm_output)}")


            # Now, access all fields using dictionary key notation ['key'] and provide defaults
            summary = review_result_structured.get('summary_of_review', "No summary provided.")
            findings = review_result_structured.get('key_findings', [])
            overall_rec = review_result_structured.get('overall_recommendation', "No overall recommendation provided.")
            disclaimer = review_result_structured.get('disclaimer', "This review is for informational purposes only and does not constitute legal advice. Please consult with a qualified legal professional for specific guidance.")

            formatted_response = f"**Overall Review Summary:**\n{summary}\n\n"
            if findings:
                formatted_response += "**Key Findings:**\n"
                for i, finding in enumerate(findings):
                    # Safely get finding attributes, providing defaults if missing
                    f_type = finding.get('type', 'N/A').replace('_', ' ').title()
                    f_severity = finding.get('severity', 'Informational').title()
                    f_context = finding.get('section_or_context', 'N/A')
                    f_description = finding.get('description', 'No description.')
                    f_recommendation = finding.get('recommendation', 'No recommendation.')

                    formatted_response += (
                        f"{i+1}. **Type:** {f_type}\n"
                        f"   **Severity:** {f_severity}\n"
                        f"   **Context:** \"{f_context}\"\n"
                        f"   **Description:** {f_description}\n"
                        f"   **Recommendation:** {f_recommendation}\n\n"
                    )
            else:
                formatted_response += "No specific key findings were identified based on your query.\n\n"

            formatted_response += f"**Overall Recommendation:**\n{overall_rec}\n\n"
            formatted_response += f"**Disclaimer:** {disclaimer}"

            logger.info("Legal review completed successfully.")
            return {
                "final_response": formatted_response,
                "review_details": review_result_structured, # Store the dict for later
                "error": None
            }
        except Exception as e:
            logger.error(f"Error during legal review: {e}", exc_info=True)
            return {
                "final_response": f"An error occurred during the legal review: {str(e)}. Please try again.",
                "error": str(e)
            }