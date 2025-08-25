# router.py (Flask)
from flask import Flask, request, jsonify
import uuid
from langgraph_manager import process_user_input, create_session, update_session
from file_handler import handle_file_upload

app = Flask(__name__)

@app.route("/query", methods=["POST"])
def query():
    user_input = request.form.get("user_input")
    session_id = request.form.get("session_id")
    file = request.files.get("file")

    # If no session_id, create new one
    if not session_id:
        session_id = create_session()

    combined_text = user_input or ""

    # If file uploaded, handle file extraction
    if file:
        file_result = handle_file_upload(file=file, session_id=session_id, filename=file.filename)

        # Update session with file metadata
        update_session(session_id, "uploaded_file", file_result)

        if file_result.get("extracted_text"):
            combined_text += "\n\n[File Content]:\n" + file_result["extracted_text"]

    # If no text and no file → error
    if not combined_text.strip():
        return jsonify({"error": "No input provided"}), 400

    # Process via LangGraph Manager
    response_data = process_user_input(combined_text, session_id=session_id)
    return jsonify(response_data)

if __name__ == "__main__":
    app.run(debug=True)
