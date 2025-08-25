#v1.0.1
# app/routes/workflow.py (UPDATED - v1.0.5)

from flask import Blueprint, request, jsonify
from app.graph.workflow import LegalWorkflow, session_histories # Import session_histories
import os
from werkzeug.utils import secure_filename
import mimetypes
from pypdf import PdfReader
import uuid # For generating session IDs

workflow_bp = Blueprint('workflow_bp', __name__)

legal_workflow_instance = LegalWorkflow()

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    print(f"DEBUG: Creating UPLOAD_FOLDER at {UPLOAD_FOLDER}")
    os.makedirs(UPLOAD_FOLDER)
else:
    print(f"DEBUG: UPLOAD_FOLDER already exists at {UPLOAD_FOLDER}")

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'md'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_document_content(document_path: str) -> str | None:
    """Helper function to load document content based on type."""
    mime_type, _ = mimetypes.guess_type(document_path)
    content = None
    try:
        if mime_type == 'application/pdf':
            reader = PdfReader(document_path)
            content_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    content_parts.append(text)
            content = "\n".join(content_parts) if content_parts else ""
            print("PDF content extracted.")
        elif mime_type == 'text/plain' or document_path.lower().endswith(('.txt', '.md')):
            with open(document_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print("Text file content extracted.")
        else:
            print(f"Unsupported file type for document loading in route: {document_path} (MIME: {mime_type})")
            return None
    except Exception as e:
        print(f"Error loading document content in route from {document_path}: {e}")
        return None
    return content


@workflow_bp.route('/process-request', methods=['POST'])
def process_request_endpoint():
    user_query = request.form.get('query')
    uploaded_file = request.files.get('file')
    # Get session_id from request headers or form data, or generate if new
    session_id = request.form.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4()) # Generate a new session ID if not provided
        print(f"DEBUG: Generated new session ID: {session_id}")

    print(f"DEBUG: Processing request for session ID: {session_id}")
    print(f"DEBUG: Received request. Query: '{user_query}', File object received: {uploaded_file is not None}")
    if uploaded_file:
        print(f"DEBUG: Uploaded file original filename: {uploaded_file.filename}")
        print(f"DEBUG: Uploaded file mimetype: {uploaded_file.mimetype}")


    if not user_query and not uploaded_file:
        print("DEBUG: Neither query nor file received. Returning 400.")
        return jsonify({"status": "error", "message": "Missing 'query' or 'file' in request payload"}), 400

    document_path = None
    initial_document_content = None

    if uploaded_file and uploaded_file.filename != '':
        print(f"DEBUG: File object is present and filename is not empty: '{uploaded_file.filename}'")
        if allowed_file(uploaded_file.filename):
            print(f"DEBUG: File type '{uploaded_file.filename.rsplit('.', 1)[1].lower()}' is allowed.")
            filename = secure_filename(uploaded_file.filename)
            document_path = os.path.join(UPLOAD_FOLDER, filename)
            print(f"DEBUG: Attempting to save file to: {os.path.abspath(document_path)}")
            try:
                uploaded_file.save(document_path)
                print(f"File saved to: {document_path}")
                
                initial_document_content = load_document_content(document_path)
                if initial_document_content is None:
                    print(f"DEBUG: Failed to load content from saved file: {document_path}. Returning 400.")
                    return jsonify({
                        "status": "error",
                        "message": "Failed to load content from the uploaded document.",
                        "classified_intent": "unclear",
                        "response_message": "I couldn't extract readable content from your document. Please ensure it's a valid text or PDF file."
                    }), 400

            except Exception as e:
                print(f"DEBUG: !!! CRITICAL ERROR !!! Error saving file or loading content: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({"status": "error", "message": f"Failed to save uploaded file: {str(e)}"}), 500
        else:
            print(f"DEBUG: File type '{uploaded_file.filename.rsplit('.', 1)[1].lower()}' is NOT allowed. Returning 400.")
            return jsonify({"status": "error", "message": "File type not allowed"}), 400
    else:
        print("DEBUG: No file uploaded or filename was empty. Proceeding without file saving.")


    print(f"Received API request for query: {user_query}")
    print(f"Document attached: {document_path is not None}")

    try:
        final_state = legal_workflow_instance.process_request(
            user_query=user_query,
            document_path=document_path,
            initial_document_content=initial_document_content,
            session_id=session_id # Pass session_id to workflow
        )

        response_status_code = 200
        response_data = {
            "status": "success",
            "original_query": user_query,
            "classified_intent": final_state.get("intent", "unclear"),
            "response_message": final_state.get("final_response", "Your request has been processed."),
            "session_id": session_id # Return session_id to client
        }

        if final_state.get("error"):
            response_data["status"] = "error"
            response_data["message"] = final_state["error"]
            if "Unsupported file type" in final_state["error"] or \
               "couldn't extract any readable content" in final_state["error"] or \
               "Required document is missing" in final_state["error"]:
                response_status_code = 400
            else:
                response_status_code = 500

        return jsonify(response_data), response_status_code

    except Exception as e:
        print(f"Unhandled error in process_request_endpoint: {e}")
        return jsonify({"status": "error", "message": f"An internal server error occurred: {str(e)}", "classified_intent": "unclear", "session_id": session_id}), 500