<div align="center">

# ⛓ AutoChain - Modular LLM Pipeline System 

**A fully local AI pipeline — no cloud, no API keys, no drama.**

Built on LangChain + Ollama · Runs on your machine · Streams in real time

<br>

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-LCEL-1C3C3C?style=for-the-badge)
![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-black?style=for-the-badge)
![Streamlit](https://img.shields.io/badge/Streamlit-Web_UI-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

<br>

</div>

---

## ✨ What is AutoChain?

AutoChain is a production-grade local AI pipeline that lets you:

- 💬 **Chat** with an LLM that remembers your conversations and searches the web when needed
- 📊 **Extract** structured financial data from earnings reports and press releases
- 📄 **Summarize** any document in seconds
- 🧠 **Reason** through complex problems with a multi-step decompose → answer → critique pipeline
- 💾 **Export** results to polished PDF or Word documents

Everything runs locally via Ollama. Your data never leaves your machine.

---

## 🖼 Interface

```
┌─────────────────────────────────────────────────────────────┐
│  ⛓ AutoChain          │  💬 Chat                           │
│  Local AI · Web-aware  │                                    │
│  ─────────────────────  │  Streams word by word ·           │
│  Model                  │  Searches web automatically ·     │
│  [qwen2.5:3b       ▼]  │  Remembers conversations          │
│                         │                                    │
│  🌐 Web search  [ON]   │  ┌──────────────────────────────┐ │
│                         │  │ How did Tesla do in Q2 2025? │ │
│  Navigation             │  └──────────────────────────────┘ │
│  ● 💬 Chat             │                                    │
│  ○ 📊 Financial        │  AutoChain ›                       │
│  ○ 📄 Summarize        │  Based on the Q2 2025 update...   │
│  ○ 🧠 Reasoning        │                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🗂 Project Structure

```
autochain/
│
├── app.py                  ← Streamlit web UI (run this)
├── main.py                 ← Interactive terminal CLI
│
├── pipeline/
│   ├── core.py             ← PipelineEngine · retry · fallback
│   ├── chains.py           ← Financial · Summarize · Reasoning chains
│   ├── prompts.py          ← PromptLibrary (default + alt variants)
│   ├── evaluators.py       ← Evaluation harness (temp × prompt sweeps)
│   ├── memory.py           ← Persistent chat memory (JSON)
│   ├── search.py           ← DuckDuckGo auto-search
│   └── export.py           ← PDF + Word export
│
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## ⚙️ Setup

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com) installed and running locally

### 1. Clone

```bash
git clone https://github.com/YOUR_USERNAME/autochain.git
cd autochain
```

### 2. Virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Pull a model

```bash
# ✅ Recommended — best JSON output, ~2GB RAM
ollama pull qwen2.5:3b

# Lightweight fallback — ~1.3GB RAM
ollama pull llama3.2:1b
```

### 5. Launch

```bash
# Web UI
streamlit run app.py

# Terminal CLI
python main.py --mode demo --model qwen2.5:3b
```

---

## 🚀 Usage

### Web UI

Open `http://localhost:8501` and pick a mode from the sidebar.

| Mode | How to use |
|------|-----------|
| 💬 **Chat** | Type anything. Searches the web automatically for current info. |
| 📊 **Financial** | Upload a `.pdf` or `.txt` → click Analyze → export results |
| 📄 **Summarize** | Upload a `.pdf` or `.txt` → click Summarize → export results |
| 🧠 **Reasoning** | Type a problem → get a step-by-step breakdown with critique |

### CLI

```bash
# Pick a mode interactively
python main.py --mode demo --model qwen2.5:3b

# Go straight to a mode
python main.py --mode financial --file report.pdf  --model qwen2.5:3b
python main.py --mode summarize --file article.txt --model qwen2.5:3b
python main.py --mode reason    --model qwen2.5:3b
python main.py --mode chat      --model qwen2.5:3b

# Run the evaluation harness (8 LLM calls)
python main.py --mode eval --file report.pdf --file2 article.txt
```

---

## 🏗 Architecture

### PipelineEngine

```
Request
  │
  ▼
Primary LLM (qwen2.5:3b)
  │
  ├─ Retry 1 ──► wait 1.5s
  ├─ Retry 2 ──► wait 3.0s
  ├─ Retry 3 ──► wait 6.0s
  │
  └─ All failed? ──► Fallback LLM
```

### FinancialChain

```
PDF / TXT
  │
  ▼
_chunk_text()         trim to max_chars, cut at sentence boundary
  │
  ▼
Prompt → LLM
  │
  ├─ Try:      JSON parse → FinancialReport ✅
  ├─ Fallback: Regex on LLM response       ⚠️
  └─ Fallback: Regex on source document    🔄
```

### ReasoningChain

```
Problem
  │
  ├─ Step 1 ── Decompose  →  numbered reasoning steps
  ├─ Step 2 ── Synthesize →  final answer + confidence
  └─ Step 3 ── Critique   →  identify weaknesses
                    │
                    ▼
             ReasoningOutput
```

### Memory

Conversations are saved to `.autochain_memory.json`:

```json
{
  "sessions": {
    "20250304_190155": {
      "title": "What is the Tesla Q2 outlook?",
      "messages": [
        { "role": "user",      "content": "...", "ts": "2025-03-04T19:01:55" },
        { "role": "assistant", "content": "...", "ts": "2025-03-04T19:02:03" }
      ]
    }
  }
}
```

Max 50 messages per session. Auto-trimmed when exceeded.

---

## 🐛 Bugs Found & Fixed

### 🔴 Bug 1 — Template variable escaping
**Error:** `KeyError: 'Input to ChatPromptTemplate is missing variables'`

LangChain's prompt templates treat `{}` as variable placeholders. JSON examples in prompts were breaking the template parser.

```python
# ❌ Broken
"Return JSON like: { \"company\": \"...\" }"

# ✅ Fixed
"Return JSON like: {{ \"company\": \"...\" }}"
```

---

### 🔴 Bug 2 — Insufficient RAM crash
**Error:** `model requires more system memory (4.8 GiB) than is available (3.3 GiB)`

`llama3.1` needs 4.8GB free RAM. Switched default to `qwen2.5:3b` (~2GB) and added document chunking to reduce context size before inference.

```python
def _chunk_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_period = truncated.rfind(".")
    return truncated[:last_period + 1] if last_period > max_chars * 0.8 else truncated
```

---

### 🔴 Bug 3 — Small model ignores JSON instructions
**Error:** `No JSON object found in LLM output`

`llama3.2:1b` responded in plain prose instead of JSON. Added a two-layer regex fallback:

```python
try:
    return FinancialReport(**_safe_parse_json(raw))      # attempt 1: JSON
except:
    report = _extract_from_plain_text(raw)               # attempt 2: regex on response
    if not any([report.company, report.revenue]):
        report = _extract_from_plain_text(chunk)         # attempt 3: regex on source
    return report
```

---

### 🔴 Bug 4 — Model switcher had no effect
**Problem:** `@st.cache_resource` cached the engine on first load and ignored sidebar model changes.

```python
# ❌ Broken — always returns the first model loaded
@st.cache_resource
def get_engine(model: str): ...

# ✅ Fixed — separate cache entry per model name
@st.cache_resource(hash_funcs={str: lambda x: x})
def get_engine(model: str): ...
```

---

### 🔴 Bug 5 — Empty label accessibility warning
**Problem:** `st.radio("")` triggered Streamlit deprecation warnings.

```python
# ❌ Before
mode = st.radio("", [...], label_visibility="collapsed")

# ✅ After
mode = st.radio("Navigation", [...], label_visibility="collapsed")
```

---

### 🔴 Bug 6 — Folder path crash
**Problem:** Pasting a folder path caused an immediate hard exit with a confusing error.

**Fix:** Detect directories, list candidate files inside, and re-prompt instead of crashing:

```
  ⚠  That's a folder, not a file.
     Files in that folder:
       • TSLA-Q2-2025-Update.pdf
       • notes.txt
```

---

### 🔴 Bug 7 — DuckDuckGo "not installed" despite being installed
**Problem:** Package was installed in global Python, but Streamlit was running inside `.venv`.

**Fix:** Always activate venv before installing:
```bash
.venv\Scripts\activate      # Windows
pip install duckduckgo-search
streamlit run app.py
```

---

## 📦 Full Dependencies

```txt
langchain
langchain-ollama
langchain-core
pydantic
streamlit
pdfplumber
python-docx
reportlab
duckduckgo-search
```

---

## 🔧 Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--model` | `qwen2.5:3b` | Ollama model tag |
| `--temp` | `0.0` | LLM temperature |
| `--mode` | `demo` | CLI mode |
| `--file` | — | Input file for financial/summarize |
| `--file2` | — | Second file for eval mode |

---

## 🚢 Pushing to GitHub

```bash
# Create .gitignore
cat > .gitignore << 'END'
.venv/
__pycache__/
*.pyc
.autochain_memory.json
*.pdf
*.docx
.env
END

# Commit and push
git init
git add .
git commit -m "feat: AutoChain v2 — LangChain + Ollama local AI pipeline"
git remote add origin https://github.com/YOUR_USERNAME/autochain.git
git branch -M main
git push -u origin main
```

---

## 📄 License

MIT — use it, fork it, build on it.

---

<div align="center">

Built with ❤️ using **LangChain** · **Ollama** · **Streamlit** · **DuckDuckGo**

*Thinks fast. Talks straight. Occasionally funny.*

</div>
