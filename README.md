# Contract Intake Agent – Interview Task

Welcome to the interview exercise repo. Your goal is to extend a lightweight LangGraph/LangChain agent so it can validate salesperson submissions, detect address issues, and emit an actionable summary for the operations team.

### Key responsibilities
1. **Normalize/validate** the incoming payload via the existing validation prompt (prefixed `validation_*`).
2. **Address validation** – Implement `validate_address_format` so it extracts street/locality/postal/country-like entities, flags missing parts, and surfaces reasons.
3. **Review summary** – Craft prompts + logic that describe captured data and call out gaps/clarifications for operations.
4. **Chatbot UX** – Collect the address interactively through the Streamlit chat UI and display validation feedback inline.


## Chatbot workflow
The Streamlit chatbot (`streamlit_app.py`) now uses an LLM-powered ingestion step (see prompts `chat_ingest_system.txt` / `chat_ingest_human.txt`) to interpret each user reply. The assistant collects the full payload (Account, Contact, Address, Notes) but only asks for the address as a single free-form string—whatever the user types is stored in `address.line1`, and the downstream validator is responsible for parsing/validating the format. Each turn is sent to the ingestion prompt, which returns a JSON payload updating the normalized fields. Once every section is captured, the agent instructs the user to type **“Confirm”**;

Customize the behavior via `app/ui/chat_flow.py` / prompts, and override the ingestion model with `CHAT_INGEST_MODEL` / `CHAT_INGEST_TEMPERATURE` env vars.

## Getting started
1. Create a virtual environment (Python 3.10+ recommended) and install dependencies:
   ```bash
   uv venv
   source .venv/bin/activate
   uv sync
   ```
2. Set any environment variables required by your LangChain/LangGraph stack (e.g., `OPENAI_API_KEY`). The chatbot ingestion uses `CHAT_INGEST_MODEL` / `CHAT_INGEST_TEMPERATURE` (defaults to `gpt-4o-mini` / `0`)

3. Spin up the chatbot UI:
   ```bash
   streamlit run streamlit_app.py
   ```
   Collect the payload via chat, validate the address inline, and type `Confirm` once all sections are captured to output the summary.

## What you still need to implement

You should manually implement below tasks:
- `validate_address_format` in `app/services/address_validation.py` – extract entities, flag missing components, and explain issues. The Streamlit UI already calls this helper, so the chat experience will only work once you complete it. [Use NER, LLM, Rule based are all ok]
- Tests under `tests/` that exercise your validator logic (replace the placeholder skip once ready).

In addition to the above, you will use a coding assistant (e.g., Codex, Claude Code, Cursor) to complete an additional coding task during the interview based on this repository. Please ensure you **have your coding assistant tool ready** before proceeding.

## API Key
You will need to provide your own OpenAI API key for this assignment. Set it as an environment variable (`OPENAI_API_KEY`) before running the application. Ensure your API key has sufficient credits and access to the required models.