"""
app.py -- AutoChain v2 Streamlit Web UI
Speed optimized: streaming responses, reduced search results, question caching.
Export: PDF + Word for Financial and Summarize modes.
"""

import hashlib
import io
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="AutoChain",
    page_icon="⛓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  .stApp { background-color: #0e1117; color: #e0e0e0; }
  section[data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
  .result-card { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 1.2rem 1.5rem; margin: 0.5rem 0; }
  .result-card p { color: #c9d1d9; margin: 0.2rem 0; }
  .metric-row { display: flex; gap: 1rem; flex-wrap: wrap; margin: 0.5rem 0; }
  .metric-chip { background: #21262d; border: 1px solid #30363d; border-radius: 20px; padding: 0.25rem 0.8rem; font-size: 0.8rem; color: #79c0ff; }
  .risk-chip { background: #2d1b1b; border: 1px solid #6e1a1a; border-radius: 20px; padding: 0.25rem 0.8rem; font-size: 0.8rem; color: #f97583; }
  .chat-user { background: #1f3a5f; border-radius: 12px 12px 2px 12px; padding: 0.7rem 1rem; margin: 0.3rem 0 0.3rem 3rem; color: #cde4ff; }
  .chat-bot { background: #1c2128; border: 1px solid #30363d; border-radius: 12px 12px 12px 2px; padding: 0.7rem 1rem; margin: 0.3rem 3rem 0.3rem 0; color: #e0e0e0; }
  .chat-ts { font-size: 0.68rem; color: #6e7681; margin-top: 0.2rem; }
  .search-badge { background: #1b3a2a; border: 1px solid #238636; border-radius: 4px; padding: 0.1rem 0.5rem; font-size: 0.72rem; color: #3fb950; margin-left: 0.5rem; }
  .cache-badge { background: #1a2a3a; border: 1px solid #1f6feb; border-radius: 4px; padding: 0.1rem 0.5rem; font-size: 0.72rem; color: #58a6ff; margin-left: 0.5rem; }
  .stButton > button { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; }
  .stButton > button:hover { background: #30363d; border-color: #58a6ff; color: #58a6ff; }
  .stTextInput > div > div > input, .stTextArea > div > div > textarea { background: #161b22 !important; color: #e0e0e0 !important; border: 1px solid #30363d !important; }
  .stFileUploader { background: #161b22; border: 1px dashed #30363d; border-radius: 8px; }
  .stTabs [data-baseweb="tab-list"] { background: #0e1117; gap: 4px; }
  .stTabs [data-baseweb="tab"] { background: #161b22; border-radius: 6px 6px 0 0; color: #8b949e; padding: 0.5rem 1.2rem; }
  .stTabs [aria-selected="true"] { background: #1f6feb !important; color: white !important; }
  hr { border-color: #30363d; }
  .stSelectbox > div > div { background: #161b22; border: 1px solid #30363d; color: #e0e0e0; }
</style>
""", unsafe_allow_html=True)


# ── Cache helpers ─────────────────────────────────────────────────────

def _cache_key(text: str) -> str:
    return hashlib.md5(text.strip().lower().encode()).hexdigest()


@st.cache_data(ttl=3600, show_spinner=False)
def cached_search(query: str) -> str:
    try:
        from pipeline.search import search_and_format
        return search_and_format(query, max_results=2)
    except Exception:
        return ""


# ── Resource helpers ──────────────────────────────────────────────────

@st.cache_resource(hash_funcs={str: lambda x: x})
def get_engine(model: str):
    from pipeline.core import PipelineEngine
    return PipelineEngine(primary_model=model, fallback_model=model, temperature=0.0)


@st.cache_resource
def get_memory():
    from pipeline.memory import ConversationMemory
    return ConversationMemory()


def load_uploaded_file(uploaded) -> str:
    suffix = Path(uploaded.name).suffix.lower()
    if suffix == ".txt":
        return uploaded.read().decode("utf-8", errors="ignore").strip()
    elif suffix == ".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(uploaded.read())) as pdf:
                return "\n\n".join(p.extract_text() or "" for p in pdf.pages).strip()
        except ImportError:
            st.error("Run: pip install pdfplumber")
            return ""
    else:
        st.error(f"Unsupported file type: {suffix}")
        return ""


def render_export_buttons(kind: str, obj, filename_stem: str):
    """
    Render PDF + Word download buttons.
    kind: 'financial' | 'summary'
    """
    from pipeline.export import (
        financial_to_pdf, financial_to_docx,
        summary_to_pdf,   summary_to_docx,
    )

    st.divider()
    st.markdown("#### 💾 Export")
    col1, col2 = st.columns(2)

    try:
        if kind == "financial":
            pdf_bytes  = financial_to_pdf(obj)
            docx_bytes = financial_to_docx(obj)
        else:
            pdf_bytes  = summary_to_pdf(obj,  source_filename=filename_stem)
            docx_bytes = summary_to_docx(obj, source_filename=filename_stem)

        with col1:
            st.download_button(
                label="⬇ Download PDF",
                data=pdf_bytes,
                file_name=f"{filename_stem}_autochain.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with col2:
            st.download_button(
                label="⬇ Download Word",
                data=docx_bytes,
                file_name=f"{filename_stem}_autochain.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
    except ImportError as e:
        st.warning(str(e))


# ── Streaming chat ────────────────────────────────────────────────────

def stream_chat(user_input: str, lc_history: list, llm, session_id: str, memory, use_search: bool):
    from langchain_core.messages import HumanMessage

    augmented = user_input
    searched = False

    if use_search:
        try:
            from pipeline.search import needs_search
            if needs_search(user_input):
                with st.spinner("🔍 Searching..."):
                    context = cached_search(user_input)
                if context:
                    augmented = f"{context}\nUser question: {user_input}"
                    searched = True
        except Exception:
            pass

    lc_history.append(HumanMessage(content=augmented))
    placeholder = st.empty()
    full_reply = ""

    try:
        for chunk in llm.stream(lc_history):
            token = chunk.content if hasattr(chunk, "content") else str(chunk)
            full_reply += token
            placeholder.markdown(
                f'<div class="chat-bot">{full_reply.replace(chr(10), "<br>")}▌</div>',
                unsafe_allow_html=True,
            )
        placeholder.markdown(
            f'<div class="chat-bot">{full_reply.replace(chr(10), "<br>")}</div>',
            unsafe_allow_html=True,
        )
    except Exception:
        placeholder.empty()
        from langchain_core.output_parsers import StrOutputParser
        try:
            response = llm.invoke(lc_history)
            full_reply = StrOutputParser().invoke(response)
        except Exception as e:
            full_reply = f"Something went wrong: {e}"

    memory.add_message(session_id, "user", user_input)
    memory.add_message(session_id, "assistant", full_reply)
    return full_reply, searched


# ── Sidebar ───────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⛓ AutoChain")
    st.markdown("<span style='color:#6e7681;font-size:0.8rem'>Local AI · Web-aware</span>", unsafe_allow_html=True)
    st.divider()

    model = st.selectbox(
        "Model",
        ["qwen2.5:3b", "llama3.2:1b", "llama3.1", "mistral:7b", "phi3:mini", "gemma3:1b"],
        index=0,
    )

    web_search_enabled = st.toggle(
        "Web search",
        value=True,
        help="Auto-search DuckDuckGo for current info (results cached 1hr)",
    )

    st.divider()
    st.markdown("### Navigation")
    mode = st.radio(
        "Navigation",
        ["💬 Chat", "📊 Financial", "📄 Summarize", "🧠 Reasoning"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown(
        "<span style='color:#6e7681;font-size:0.75rem'>Powered by Ollama + LangChain + DDG</span>",
        unsafe_allow_html=True,
    )


# ── Chat ──────────────────────────────────────────────────────────────

if mode == "💬 Chat":
    st.markdown("## 💬 Chat")
    st.markdown(
        "<span style='color:#6e7681'>Streams word by word · Searches web automatically · Remembers conversations</span>",
        unsafe_allow_html=True,
    )

    memory = get_memory()

    col1, col2 = st.columns([3, 1])
    with col1:
        sessions = memory.list_sessions()
        session_options = {s["id"]: f"{s['title']} ({s['message_count']} msgs)" for s in sessions}

        if "current_session" not in st.session_state or st.session_state.current_session not in session_options:
            st.session_state.current_session = memory.new_session()
            session_options = {
                s["id"]: f"{s['title']} ({s['message_count']} msgs)"
                for s in memory.list_sessions()
            }

        selected = st.selectbox(
            "Conversation",
            options=list(session_options.keys()),
            format_func=lambda x: session_options.get(x, x),
            index=0,
        )
        if selected != st.session_state.current_session:
            st.session_state.current_session = selected

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("＋ New", use_container_width=True):
            st.session_state.current_session = memory.new_session()
            st.rerun()
        if st.button("🗑 Delete", use_container_width=True):
            memory.delete_session(st.session_state.current_session)
            st.session_state.current_session = memory.new_session()
            st.rerun()

    st.divider()

    messages = memory.get_messages(st.session_state.current_session)
    if not messages:
        st.markdown(
            "<div style='color:#6e7681;text-align:center;padding:2rem'>Start a conversation below 👇</div>",
            unsafe_allow_html=True,
        )

    for msg in messages:
        ts = msg.get("ts", "")[:16].replace("T", " ")
        if msg["role"] == "user":
            st.markdown(
                f'<div class="chat-user">{msg["content"]}'
                f'<div class="chat-ts">You · {ts}</div></div>',
                unsafe_allow_html=True,
            )
        else:
            content = msg["content"].replace("\n", "<br>")
            badge = '<span class="search-badge">🌐 web search</span>' if msg.get("searched") else ""
            st.markdown(
                f'<div class="chat-bot">{content}'
                f'<div class="chat-ts">AutoChain · {ts}{badge}</div></div>',
                unsafe_allow_html=True,
            )

    st.divider()

    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "Message",
            placeholder="Ask me anything — current events, finance, code, ideas...",
            height=80,
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Send →", use_container_width=True, type="primary")

    if submitted and user_input.strip():
        session_id = st.session_state.current_session
        engine = get_engine(model)
        llm = engine.get_llm()
        lc_history = memory.to_langchain_messages(session_id)

        st.markdown(
            f'<div class="chat-user">{user_input.strip()}'
            f'<div class="chat-ts">You · now</div></div>',
            unsafe_allow_html=True,
        )

        reply, searched = stream_chat(
            user_input.strip(), lc_history, llm,
            session_id, memory, web_search_enabled,
        )
        st.rerun()


# ── Financial ─────────────────────────────────────────────────────────

elif mode == "📊 Financial":
    st.markdown("## 📊 Financial Extraction")
    st.markdown(
        "<span style='color:#6e7681'>Upload an earnings report, press release, or any financial document.</span>",
        unsafe_allow_html=True,
    )
    st.divider()

    uploaded = st.file_uploader("Upload file", type=["txt", "pdf"], label_visibility="collapsed")

    if uploaded:
        with st.spinner(f"Reading {uploaded.name}..."):
            text = load_uploaded_file(uploaded)

        if text:
            st.success(f"Loaded **{uploaded.name}** — {len(text):,} chars")
            col1, col2 = st.columns([1, 3])
            with col1:
                max_chars = st.slider("Context window (chars)", 2000, 12000, 6000, 500)
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                analyze = st.button("Analyze →", type="primary", use_container_width=True)

            if analyze:
                cache_key = _cache_key(text[:500] + str(max_chars) + model)
                if f"fin_{cache_key}" in st.session_state:
                    report = st.session_state[f"fin_{cache_key}"]
                    st.info("⚡ Loaded from cache")
                else:
                    with st.spinner("Extracting financial data..."):
                        from pipeline.chains import FinancialChain
                        engine = get_engine(model)
                        chain = FinancialChain(engine.get_llm())
                        report = chain.run(text, max_chars=max_chars)
                    st.session_state[f"fin_{cache_key}"] = report

                st.divider()
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Company",    report.company    or "—")
                c2.metric("Revenue",    report.revenue    or "—")
                c3.metric("Net Income", report.net_income or "—")
                c4.metric("EBITDA",     report.ebitda     or "—")
                st.divider()

                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("#### 📈 Key Metrics")
                    if report.key_metrics:
                        chips = " ".join(f'<span class="metric-chip">{m}</span>' for m in report.key_metrics)
                        st.markdown(f'<div class="metric-row">{chips}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown("<span style='color:#6e7681'>None extracted</span>", unsafe_allow_html=True)
                with col_b:
                    st.markdown("#### ⚠️ Risk Factors")
                    if report.risks:
                        chips = " ".join(f'<span class="risk-chip">{r}</span>' for r in report.risks)
                        st.markdown(f'<div class="metric-row">{chips}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown("<span style='color:#6e7681'>None extracted</span>", unsafe_allow_html=True)

                if report.outlook:
                    st.divider()
                    st.markdown("#### 🔭 Outlook")
                    st.markdown(
                        f'<div class="result-card"><p>{report.outlook}</p></div>',
                        unsafe_allow_html=True,
                    )

                # ── Export buttons ──
                render_export_buttons("financial", report, Path(uploaded.name).stem)


# ── Summarize ─────────────────────────────────────────────────────────

elif mode == "📄 Summarize":
    st.markdown("## 📄 Document Summarization")
    st.markdown(
        "<span style='color:#6e7681'>Upload any document — article, report, paper, notes.</span>",
        unsafe_allow_html=True,
    )
    st.divider()

    uploaded = st.file_uploader("Upload file", type=["txt", "pdf"], label_visibility="collapsed")

    if uploaded:
        with st.spinner(f"Reading {uploaded.name}..."):
            text = load_uploaded_file(uploaded)

        if text:
            st.success(f"Loaded **{uploaded.name}** — {len(text):,} chars")
            col1, col2 = st.columns([1, 3])
            with col1:
                max_chars = st.slider("Context window (chars)", 2000, 12000, 6000, 500)
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                summarize = st.button("Summarize →", type="primary", use_container_width=True)

            if summarize:
                cache_key = _cache_key(text[:500] + str(max_chars) + model)
                if f"sum_{cache_key}" in st.session_state:
                    result = st.session_state[f"sum_{cache_key}"]
                    st.info("⚡ Loaded from cache")
                else:
                    with st.spinner("Summarizing..."):
                        from pipeline.chains import SummarizationChain
                        engine = get_engine(model)
                        chain = SummarizationChain(engine.get_llm())
                        result = chain.run(text, max_chars=max_chars)
                    st.session_state[f"sum_{cache_key}"] = result

                st.divider()
                st.markdown("#### Summary")
                st.markdown(
                    f'<div class="result-card"><p>{result.raw_summary.replace(chr(10), "<br>")}</p></div>',
                    unsafe_allow_html=True,
                )

                # ── Export buttons ──
                render_export_buttons("summary", result, Path(uploaded.name).stem)


# ── Reasoning ─────────────────────────────────────────────────────────

elif mode == "🧠 Reasoning":
    st.markdown("## 🧠 Multi-step Reasoning")
    st.markdown(
        "<span style='color:#6e7681'>Give me any problem or decision. I'll break it down, answer it, then critique my own answer.</span>",
        unsafe_allow_html=True,
    )
    st.divider()

    problem = st.text_area(
        "Problem or question",
        placeholder="e.g. Should we prioritize feature A or B given our runway?",
        height=140,
        label_visibility="collapsed",
    )

    if st.button("Reason through it →", type="primary"):
        if not problem.strip():
            st.warning("Type a problem first.")
        else:
            cache_key = _cache_key(problem.strip() + model)
            if f"rsn_{cache_key}" in st.session_state:
                result = st.session_state[f"rsn_{cache_key}"]
                st.info("⚡ Loaded from cache")
            else:
                with st.spinner("Breaking it down..."):
                    from pipeline.chains import ReasoningChain
                    engine = get_engine(model)
                    chain = ReasoningChain(engine.get_llm())
                    result = chain.run(problem.strip())
                st.session_state[f"rsn_{cache_key}"] = result

            st.divider()
            confidence_color = {
                "High": "#3fb950", "Medium": "#d29922", "Low": "#f85149"
            }.get(result.confidence, "#8b949e")
            st.markdown(
                f"Confidence: <span style='color:{confidence_color};font-weight:bold'>{result.confidence}</span>",
                unsafe_allow_html=True,
            )
            st.divider()

            tab1, tab2, tab3 = st.tabs(["🪜 Reasoning Steps", "✅ Final Answer", "🔍 Critique"])
            with tab1:
                st.markdown(
                    f'<div class="result-card"><p>{result.steps.replace(chr(10), "<br>")}</p></div>',
                    unsafe_allow_html=True,
                )
            with tab2:
                st.markdown(
                    f'<div class="result-card"><p>{result.final_answer.replace(chr(10), "<br>")}</p></div>',
                    unsafe_allow_html=True,
                )
            with tab3:
                st.markdown(
                    f'<div class="result-card"><p>{result.critique.replace(chr(10), "<br>")}</p></div>',
                    unsafe_allow_html=True,
                )