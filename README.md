
# 🧠 Resume RAG AI Agent

An intelligent agent that automatically fills out job application forms using information extracted from a candidate's resume, powered by **LLMs**, **RAG**, and a **multi-turn feedback loop**.

---

## ✨ What It Does

This project automates the process of filling job application forms by:

- Parsing resumes and application forms (PDFs) using **LlamaParse**
- Extracting required fields using **structured prompting**
- Using **RAG (Retrieval-Augmented Generation)** to answer field-specific questions from the resume
- Supporting **multi-turn human feedback** to refine and improve responses
- Finalizing the completed form with human approval

---

## 🛠 Tech Stack

- **LLMs**: OpenAI (e.g., `gpt-4o-mini`)
- **Embedding Model**: `text-embedding-3-small` via OpenAI
- **Parsing**: LlamaParse (LlamaCloud)
- **Vector Store**: LlamaIndex's `VectorStoreIndex`
- **Frontend**: Gradio
- **Workflow Engine**: `llama_index.core.workflow`
- **Feedback Matching**: `rapidfuzz` for fuzzy field matching
- **Async Infra**: `asyncio`, `nest_asyncio`

---

## 🧩 Project Structure

```

app/
├── config.py            # Environment variable setup
├── events.py            # Custom workflow events
├── helper.py            # Key loading utils
├── llm\_utils.py         # LLM and embed model loaders
├── main.py              # Session management and feedback logic
├── parser.py            # Resume & form parsing via LlamaParse
├── workflow\.py          # RAG + feedback-driven workflow
frontend/
└── ui.py                # Gradio UI interface

````

---

## 🚀 How to Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
````

Dependencies include:

```
openai
llama-index
llama-parse
gradio
python-dotenv
rapidfuzz
nest_asyncio
```

### 2. Create a `.env` file

```env
OPENAI_API_KEY=your_openai_key
LLAMA_CLOUD_API_KEY=your_llama_key
LLAMA_CLOUD_BASE_URL=https://api.llamaindex.ai
```

### 3. Start the UI

```bash
python frontend/ui.py
```

---

## 💡 Features

✅ Automated parsing and field extraction

✅ Resume-to-form mapping via RAG

✅ Multi-turn feedback loop (refine form answers interactively)

✅ Persistent resume caching using SHA256

✅ Modular LLM-based workflow with custom events

✅ Simple web UI using Gradio

---

## 🤖 Multi-Turn Feedback Handling

After the initial form is filled, the user can:

* Provide **freeform feedback** (example, *"Add LinkedIn link to contact info"*)
* The system uses approximate string matching to map feedback to relevant fields
* Regenerates answers only for affected fields
* Repeats until the user confirms with "done"

