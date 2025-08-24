🚦 Build Order (from blank to multi-agent)
Phase 0 — already done

.env, .gitignore, config.py

core/openrouter_client.py (v1 SDK style)

agents/classifier_agent.py (legal-only, mixed-query flags)

Phase 1 — wire up the HTTP surface (hello world → classify)

app.py

Flask app, /health and /query routes.

/query should: parse JSON → call core/router.route_query() → return its JSON.

Done check: GET /health returns {status: ok}.

core/router.py

route_query(session_id, user_input):

call agents.classifier_agent.classify_intent()

if legal_related == False: return {"message": "I can only assist with legal topics."}

attach note if unrelated_detected == True: "Ignoring unrelated non-legal parts."

for now (MVP), directly dispatch to a single agent: insights_agent for insights, else echo the classification. We’ll swap to LangGraph in Phase 3.

Done check: POST /query with a legal question returns JSON classification (and a note for mixed queries).

Phase 2 — minimum viable agents (answer something useful)

agents/insights_agent.py

Function: run(user_input, session_ctx)

Use generate_response(..., model="openai/gpt-4o", use_web=True)

System prompt: “AI paralegal, legal topics only; cite sources as markdown links; if non-legal, refuse.”

Done check: Ask “Compare GDPR and CCPA for SMBs”—get a substantive, cited answer + your note if mixed.

agents/summarize_agent.py

run(user_input, session_ctx) → summarize provided text/snippet (with :online on only if needed).

Done check: POST /query with “Summarize this: <text>” returns a summary.

agents/compare_agent.py

run(user_input, session_ctx) → structured side-by-side bullets + citation hinting (with :online).

Done check: Returns a clean comparison table/bullets.

agents/greeting_agent.py & agents/unclear_agent.py

Tiny responders:

greeting → short hello + “I can assist with legal topics.”

unclear → “Please rephrase a legal question.”

Done check: Greetings or vague inputs respond without web.

You now “answer” most flows even before LangGraph.

Phase 3 — orchestration with LangGraph (replace ad-hoc dispatch)

core/langgraph_manager.py

Define a simple graph:

Nodes: classify, insights, draft, update, review, compare, summarize, greeting, unclear.

Edges: classify -> {next agent} based on primary intent.

State object: {"session_id", "user_input", "classification", "context"}.

Public entry: run_graph(session_id, user_input).

In nodes, call the corresponding agent’s run().

Done check: In core/router.py, replace direct dispatch with langgraph_manager.run_graph() and responses still work.

Phase 4 — basic memory (session-aware answers)

core/memory.py

Minimal session memory (dict or SQLite):

get_session_ctx(session_id) → returns {"history": [...], "last_docs": [...]}.

append_history(session_id, role, content).

For MVP, use a module-level dict; later swap to SQLite.

Agents read a few recent turns to add short context in the system prompt (e.g., “User previously asked about GDPR consent.”).

Done check: Ask a follow-up (“expand the deletion rights part”) and see it uses prior context.

Phase 5 — remaining task agents

agents/draft_agent.py

run() → generate first-pass legal templates (NDA, cease & desist, etc.) with placeholders and “not legal advice” disclaimer; :online for recent law references if needed.

Done check: “Draft an NDA for a SaaS startup in India” returns a structured draft.

agents/review_agent.py

run() → critique and risk flags; list missing clauses; suggest improvements; optional :online for standards.

Done check: Paste a lease; get structured issues + suggestions.

agents/update_agent.py

run() → accept base text + change request; produce a diff-style or replaced clause block.

Done check: “Update termination clause to 90 days notice” returns only the revised section plus rationale.

Phase 6 — polish, reliability, ops

core/router.py (enhance)

Add request schema validation:

require input, optional session_id (generate if missing).

Envelope responses:

{
  "intent": {...},
  "note": "...",
  "output": "...",
  "citations": [...],
  "session_id": "..."
}


Map each agent’s result into this shape.

Logging

Lightweight app logging to logs/app.log from app.py (Flask before/after request hooks).

Log session_id, latency, model used, use_web flag, and token estimates if you add them later.

requirements.txt

Freeze after you confirm everything runs:

flask, openai, langchain, langgraph, python-dotenv

(optional) chromadb or sqlite-utils if you later persist memory.

🧭 Quick checklist per step (copy/paste as you go)

app.py → routes to core.router.route_query ✅

core/router.py → uses classifier, legal filter, temp dispatch ✅

agents/insights_agent.py → real answer with :online ✅

agents/summarize_agent.py ✅

agents/compare_agent.py ✅

agents/greeting_agent.py, agents/unclear_agent.py ✅

core/langgraph_manager.py → orchestrate agents ✅

core/memory.py → in-memory session context ✅

agents/draft_agent.py ✅

agents/review_agent.py ✅

agents/update_agent.py ✅

Router response envelope + logging ✅

Freeze requirements.txt ✅

🧪 Manual “done checks” (curl)

Health

curl http://127.0.0.1:5000/health


Insights

curl -X POST http://127.0.0.1:5000/query \
  -H "Content-Type: application/json" \
  -d '{"input":"Compare GDPR and CCPA for small businesses"}'


Mixed query

curl -X POST http://127.0.0.1:5000/query \
  -H "Content-Type: application/json" \
  -d '{"input":"GDPR rights. also write c++ hello world"}'


Expect: legal answer + "note": "Ignoring unrelated non-legal parts."






paralegal-backend/
│── app.py
│── config.py
│── requirements.txt
│── README.md
│
├── core/
│   ├── router.py
│   ├── memory.py
│   ├── openrouter_client.py
│   ├── document_parser.py
│   └── langgraph_manager.py
|
│
├── agents/
│   ├── __init__.py
│   ├── classifier_agent.py
│   ├── insights_agent.py
│   ├── draft_agent.py
│   ├── update_agent.py
│   ├── review_agent.py
│   ├── compare_agent.py
│   ├── summarize_agent.py
│   ├── greeting_agent.py
│   └── unclear_agent.py
│
├── data/
│   ├── memory_store.db
│   └── vector_index/
│
└── logs/
    └── app.log


flowchart TD
  A[User Input/Upload] --> B{Classifier Agent}
  B -->|Intent = Draft| C[Draft Agent]
  B -->|Intent = Review| D[Review Agent]
  B -->|Intent = Compare| E[Compare Agent]
  B -->|Unclear| F[Unclear Agent]

  B --> G{Case Relevance?}
  G -->|Same| H[Continue Current Case]
  G -->|New| I[Ask to Create New Case Session]
