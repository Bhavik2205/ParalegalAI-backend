# from agents import classify_intent

# if __name__ == "__main__":
#     query = " can you write simple c++ hello world. GDPR vs CCPA regulations for small businesses."
#     result = classify_intent(query)
#     print(result)
#     # Expected: {"primary_intent": "compare", "secondary_intent": "insights"}


from flask import Flask, request, jsonify
from core.router import route_query
import uuid

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/query', methods=['POST'])
def query():
    try:
        data = request.get_json()
        if not data or "input" not in data:
            return jsonify({"error": "Missing 'input' field"}), 400

        user_input = data["input"]
        session_id = data.get("session_id", str(uuid.uuid4()))

        response = route_query(session_id, user_input)
        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
