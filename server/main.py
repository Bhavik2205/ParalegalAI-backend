# # server/main.py
# from flask import Flask, jsonify
# from flask_cors import CORS # To handle CORS for frontend integration
# from app.config import Config
# from app.routes.workflow import workflow_bp
# import os
# import logging
# import sys # Import sys for sys.exit()

# # Configure logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# def create_app():
#     app = Flask(__name__)
#     app.config.from_object(Config)

#     # Enable CORS for all origins for development (be more restrictive in production!)
#     CORS(app)

#     # Register blueprints
#     app.register_blueprint(workflow_bp, url_prefix='/api')

#     @app.route('/')
#     def health_check():
#         return jsonify({"status": "Legal Assistant API is running!"}), 200

#     # Basic error handler example
#     @app.errorhandler(404)
#     def not_found(error):
#         return jsonify({"error": "Not Found", "message": "The requested URL was not found on the server."}), 404

#     @app.errorhandler(500)
#     def internal_server_error(error):
#         return jsonify({"error": "Internal Server Error", "message": "Something went wrong on the server."}), 500

#     return app

# # The standard way to run a Flask app
# if __name__ == '__main__':
#     app = create_app()
#     # Check if OPENAI_API_KEY is loaded
#     # This check assumes your Config class correctly loads OPENAI_API_KEY
#     if not app.config.get('OPENAI_API_KEY'): # Use .get() for safer access
#         logging.error("OPENAI_API_KEY is not set. Please ensure it's in your .env file or environment variables.")
#         # Optionally exit or prevent server from starting if critical config is missing
#         # For production, you might want to uncomment sys.exit(1)
#         # sys.exit(1)
#     else:
#         logging.info("OPENAI_API_KEY loaded successfully.")

#     # Firebase service initialization (optional here, depends on first usage)
#     # The FirestoreService is designed to initialize on first use, but you could explicitly
#     # try to initialize it here if you want to catch credential errors early.
#     # from app.services.firestore_service import FirestoreService
#     # try:
#     #     _ = FirestoreService().get_db()
#     #     logging.info("Firebase Firestore client initialized successfully.")
#     # except Exception as e:
#     #     logging.error(f"Failed to initialize Firebase Firestore: {e}")


#     app.run(debug=True, port=5000) # debug=True is good for development, disable in production



import os
import mimetypes
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pypdf import PdfReader
from app.graph.workflow import LegalWorkflow, session_histories # Corrected import
from app.config import Config
import logging
import uuid
from langchain_core.messages import HumanMessage, AIMessage # Ensure these are imported if used for history management

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

CORS(app, resources={r"/api/*": {"origins": "*"}})

# Ensure UPLOAD_FOLDER exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
    logger.debug(f"UPLOAD_FOLDER created at {app.config['UPLOAD_FOLDER']}")
else:
    logger.debug(f"UPLOAD_FOLDER already exists at {app.config['UPLOAD_FOLDER']}")

# Initialize the workflow
legal_workflow = LegalWorkflow()

@app.route('/')
def index():
    return "Legal AI Assistant Backend is running!"

@app.route('/api/process-request', methods=['POST'])
def process_request_endpoint():
    session_id = request.headers.get('X-Session-ID') or request.form.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        logger.debug(f"Generated new session ID: {session_id}")
    else:
        logger.debug(f"Processing request for session ID: {session_id}")

    user_query = request.form.get('query', '')
    uploaded_file = request.files.get('file')

    logger.debug(f"Received request. Query: '{user_query}', File object received: {bool(uploaded_file)}")

    document_path = None
    document_content = None

    if uploaded_file and uploaded_file.filename:
        logger.debug(f"Uploaded file original filename: {uploaded_file.filename}")
        logger.debug(f"Uploaded file mimetype: {uploaded_file.mimetype}")

        file_extension = os.path.splitext(uploaded_file.filename)[1].lower()
        if file_extension not in app.config['ALLOWED_EXTENSIONS']:
            logger.error(f"File type '{file_extension}' not allowed.")
            return jsonify({"error": f"File type '{file_extension}' not allowed. Supported types: {', '.join(app.config['ALLOWED_EXTENSIONS'])}."}), 400

        filename = f"{uuid.uuid4()}{file_extension}"
        document_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        try:
            logger.debug(f"File object is present and filename is not empty: '{uploaded_file.filename}'")
            logger.debug(f"File type '{file_extension.lstrip('.')}' is allowed.")
            logger.debug(f"Attempting to save file to: {document_path}")
            uploaded_file.save(document_path)
            logger.info(f"File saved to: {document_path}")

            if file_extension == '.pdf':
                try:
                    reader = PdfReader(document_path)
                    document_content = ""
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            document_content += page_text + "\n"
                    logger.info("PDF content extracted.")
                except Exception as e:
                    logger.error(f"Failed to extract content from PDF: {e}")
                    return jsonify({"error": f"Failed to extract readable content from PDF: {str(e)}. Please ensure it's a valid PDF."}), 400
            elif file_extension in ['.txt', '.md']:
                with open(document_path, 'r', encoding='utf-8') as f:
                    document_content = f.read()
                logger.info(f"{file_extension.lstrip('.').upper()} content extracted.")
            # Add .docx support here if you choose to implement it, using python-docx
            # elif file_extension == '.docx':
            #     from docx import Document
            #     doc = Document(document_path)
            #     document_content = "\n".join([p.text for p in doc.paragraphs])
            #     logger.info("DOCX content extracted.")
            else:
                logger.error(f"Unsupported file type for content extraction: {document_path} (Extension: {file_extension})")
                return jsonify({"error": "Unsupported file type for content extraction. Only PDF, TXT, MD are fully supported for content extraction. DOCX requires additional libraries."}), 400

        except Exception as e:
            logger.error(f"Failed to save or process file: {document_path}. Error: {e}", exc_info=True)
            return jsonify({"error": f"Failed to save or process file: {str(e)}"}), 500
    else:
        logger.debug("No file uploaded or filename was empty. Proceeding without file saving.")

    logger.info(f"Received API request for query: {user_query}")
    logger.info(f"Document attached: {bool(document_path)}")

    # The check for 'confirmation_pending_from_previous_turn' is removed here,
    # as the routing logic in workflow.py's _route_after_confirmation
    # is now responsible for interpreting the user's response to a prior confirmation request.

    workflow_output = legal_workflow.process_request(
        user_query=user_query,
        document_path=document_path,
        initial_document_content=document_content,
        session_id=session_id
    )

    if document_path and not app.config.get('KEEP_UPLOADS', False):
        try:
            os.remove(document_path)
            logger.debug(f"Cleaned up uploaded file: {document_path}")
        except Exception as e:
            logger.error(f"Error cleaning up file {document_path}: {e}")

    response_data = {
        "response": workflow_output.get("final_response", "I'm sorry, I couldn't process your request."),
        "session_id": session_id,
        "error": workflow_output.get("error"),
        "review_details": workflow_output.get("review_details"),
        "confirmation_pending_for_review": workflow_output.get("confirmation_pending_for_review", False)
    }

    # Determine HTTP status code
    # Return 200 OK for most responses, even if they are asking for more info or clarifying.
    # Only return 500 for genuine, unexpected server-side errors that prevent a meaningful response.
    status_code = 200 # Default to 200 OK
    if workflow_output.get("error") and \
       "Required document is missing" not in workflow_output["error"] and \
       "Unsupported file type" not in workflow_output["error"] and \
       "Failed to extract readable content" not in workflow_output["error"] and \
       "An unexpected error occurred during workflow processing" not in workflow_output["error"]:
        # If there's an error and it's NOT one of the user-facing expected "errors" or a general unhandled workflow error,
        # then it's a true server error (500).
        status_code = 500
    # Special case: If the error explicitly mentions "An unexpected error occurred during workflow processing"
    # or if the error is present and not one of the "expected" user-facing messages, treat as 500.
    elif workflow_output.get("error") and (
        "An unexpected error occurred during workflow processing" in workflow_output["error"] or
        (workflow_output.get("error") not in ["Required document is missing.", "Unsupported file type.", "Failed to extract readable content."])
    ):
        status_code = 500


    return jsonify(response_data), status_code

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    Config.load_openai_api_key()
    app.run(debug=True, port=5000)