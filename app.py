"""app.py - Nudge Streamlit Application.

Hacktoberfest 2026 "Build for a Friend" Challenge.
Turn messy thoughts into actionable tasks using local Gemma 3 via Ollama.
"""

import datetime
import json
import streamlit as st

import ai

# Page configuration
st.set_page_config(
    page_title="Nudge — Turn messy thoughts into actionable tasks",
    page_icon="✦",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Custom minimalist styling inspired by modern craft software
st.markdown(
    """
<style>
    /* Global layout & typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .main .block-container {
        max-width: 680px;
        padding-top: 2.5rem;
        padding-bottom: 4rem;
    }

    /* Hide standard Streamlit header & footer elements for clean product feel */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Brand Header */
    .brand-container {
        text-align: center;
        margin-bottom: 2rem;
    }

    .brand-logo {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        font-size: 1.85rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        color: #111827;
        margin-bottom: 0.35rem;
    }

    @media (prefers-color-scheme: dark) {
        .brand-logo { color: #f9fafb; }
    }

    .brand-logo span.sparkle {
        color: #6366f1;
        font-size: 1.5rem;
    }

    .brand-tagline {
        font-size: 1.15rem;
        font-weight: 500;
        color: #4b5563;
        line-height: 1.4;
        margin-bottom: 0.2rem;
    }

    @media (prefers-color-scheme: dark) {
        .brand-tagline { color: #9ca3af; }
    }

    .brand-subtagline {
        font-size: 0.95rem;
        font-weight: 400;
        color: #6b7280;
    }

    /* Local status indicator */
    .local-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 9999px;
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.25);
        color: #059669;
        font-size: 0.76rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        margin-top: 0.75rem;
    }

    .local-pill .dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background-color: #10b981;
    }

    /* Input area card */
    .input-label {
        font-size: 1.05rem;
        font-weight: 600;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }

    @media (prefers-color-scheme: dark) {
        .input-label { color: #e5e7eb; }
    }

    /* Example prompt chips */
    .examples-header {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #6b7280;
        margin-top: 0.6rem;
        margin-bottom: 0.35rem;
        font-weight: 600;
    }

    /* Task Card */
    .task-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1rem 1.15rem;
        margin-bottom: 0.85rem;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }

    @media (prefers-color-scheme: dark) {
        .task-card {
            background: #18181b;
            border-color: #27272a;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
        }
    }

    .task-card:hover {
        border-color: #d1d5db;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.06);
    }

    @media (prefers-color-scheme: dark) {
        .task-card:hover {
            border-color: #3f3f46;
        }
    }

    .task-title {
        font-size: 1.02rem;
        font-weight: 600;
        color: #111827;
        margin-bottom: 0.4rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    @media (prefers-color-scheme: dark) {
        .task-title { color: #f4f4f5; }
    }

    .task-meta-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
        font-size: 0.84rem;
        color: #6b7280;
    }

    @media (prefers-color-scheme: dark) {
        .task-meta-row { color: #a1a1aa; }
    }

    .meta-separator {
        color: #d1d5db;
        font-weight: 300;
    }

    @media (prefers-color-scheme: dark) {
        .meta-separator { color: #3f3f46; }
    }

    /* Badges */
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 7px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: capitalize;
    }

    .badge-priority-high {
        background: #fee2e2;
        color: #b91c1c;
    }
    .badge-priority-medium {
        background: #fef3c7;
        color: #b45309;
    }
    .badge-priority-low {
        background: #dcfce7;
        color: #15803d;
    }

    @media (prefers-color-scheme: dark) {
        .badge-priority-high { background: rgba(239, 68, 68, 0.2); color: #fca5a5; }
        .badge-priority-medium { background: rgba(245, 158, 11, 0.2); color: #fcd34d; }
        .badge-priority-low { background: rgba(16, 185, 129, 0.2); color: #86efac; }
    }

    .badge-category {
        background: #f3f4f6;
        color: #374151;
        border: 1px solid #e5e7eb;
    }

    @media (prefers-color-scheme: dark) {
        .badge-category {
            background: #27272a;
            color: #d4d4d8;
            border-color: #3f3f46;
        }
    }

    /* Results section title */
    .section-headline {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: 1.8rem;
        margin-bottom: 0.9rem;
    }

    .section-count {
        font-size: 0.95rem;
        font-weight: 600;
        color: #111827;
    }

    @media (prefers-color-scheme: dark) {
        .section-count { color: #f3f4f6; }
    }

    .section-badge-group {
        font-size: 0.74rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #6b7280;
    }

    /* Why Nudge Box */
    .why-nudge-box {
        background: #f9fafb;
        border: 1px dashed #d1d5db;
        border-radius: 10px;
        padding: 0.85rem 1rem;
        font-size: 0.86rem;
        color: #4b5563;
        margin-top: 0.5rem;
        margin-bottom: 1.5rem;
    }

    @media (prefers-color-scheme: dark) {
        .why-nudge-box {
            background: #18181b;
            border-color: #3f3f46;
            color: #a1a1aa;
        }
    }

    .why-nudge-bullet {
        margin-bottom: 0.35rem;
        line-height: 1.4;
    }

    .why-nudge-bullet:last-child {
        margin-bottom: 0;
    }

    /* Footer local notice */
    .local-footer {
        text-align: center;
        margin-top: 3.5rem;
        padding-top: 1.25rem;
        border-top: 1px solid #e5e7eb;
        font-size: 0.8rem;
        color: #9ca3af;
    }

    @media (prefers-color-scheme: dark) {
        .local-footer {
            border-color: #27272a;
            color: #71717a;
        }
    }
</style>
""",
    unsafe_allow_html=True,
)

# Benchmark test cases for fast testing / judge evaluation
BENCHMARK_EXAMPLES = [
    {
        "label": "Test 1: DBMS assignment (Tomorrow)",
        "text": "Tomorrow I need to finish my DBMS assignment.",
    },
    {
        "label": "Test 2: Rahul & GitHub link (Tonight)",
        "text": "Tonight call Rahul about our project and remind me to send him the GitHub link.",
    },
    {
        "label": "Test 3: Pay Ahmed ₹500 (Friday)",
        "text": "I need to pay Ahmed ₹500 on Friday.",
    },
    {
        "label": "Test 4: Clean laptop (This week)",
        "text": "I should clean my laptop sometime this week.",
    },
    {
        "label": "Test 5: Empty actions (Nothing urgent)",
        "text": "I have nothing urgent today.",
    },
    {
        "label": "Test 6: Multi-task rush (4 tasks)",
        "text": "Tomorrow morning submit the assignment, call mom tonight, buy groceries after college, and pay the electricity bill before Friday.",
    },
]

# Initialize Session State
if "input_area" not in st.session_state:
    st.session_state.input_area = ""
if "extracted_tasks" not in st.session_state:
    st.session_state.extracted_tasks = None
if "status_error" not in st.session_state:
    st.session_state.status_error = None

# Quick connectivity probe
ollama_ok, ollama_msg, models = ai.check_ollama_status()
detected_model = ai.detect_gemma_model(models) if ollama_ok else None

# Header Section
st.markdown(
    f"""
<div class="brand-container">
    <div class="brand-logo">
        <span class="sparkle">✦</span> Nudge
    </div>
    <div class="brand-tagline">
        Turn messy thoughts into actionable tasks.
    </div>
    <div class="brand-subtagline">
        Say it. Nudge gets it done.
    </div>
    <div>
        <span class="local-pill">
            <span class="dot"></span>
            {'Powered locally by Gemma (' + (detected_model or 'gemma3:1b') + ') via Ollama' if ollama_ok else 'Ollama Offline'}
        </span>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# Ollama offline banner if daemon not running
if not ollama_ok:
    st.error(
        f"**Nudge can't connect to Ollama.** Make sure Ollama is running locally.\n\n"
        f"Run in your terminal:\n```bash\nollama serve\n```"
    )
elif not detected_model:
    st.warning(
        f"**The configured Gemma model isn't available locally.**\n\n"
        f"Expected model: `{ai.DEFAULT_GEMMA_MODEL}`\n\n"
        f"Run in your terminal:\n```bash\nollama pull {ai.DEFAULT_GEMMA_MODEL}\n```"
    )

# Input Section
st.markdown('<div class="input-label">What\'s on your mind?</div>', unsafe_allow_html=True)

# Callback for example selection
def load_example():
    choice = st.session_state.get("example_selector")
    for item in BENCHMARK_EXAMPLES:
        if item["label"] == choice:
            st.session_state.input_area = item["text"]
            break

# Example selector dropdown for seamless demoing
cols_ex = st.columns([3, 1])
with cols_ex[0]:
    example_options = ["Choose a sample test note..."] + [e["label"] for e in BENCHMARK_EXAMPLES]
    st.selectbox(
        "Load example note",
        options=example_options,
        index=0,
        key="example_selector",
        on_change=load_example,
        label_visibility="collapsed",
    )

# Text Area
placeholder_text = "Tomorrow I need to finish my DBMS assignment, call Rahul tonight about the project, and pay Ahmed ₹500 on Friday."

user_text = st.text_area(
    label="Messy thought note",
    placeholder=placeholder_text,
    height=125,
    key="input_area",
    label_visibility="collapsed",
)

# Action Buttons Row
col_btn1, col_btn2 = st.columns([1, 1])

with col_btn1:
    nudge_clicked = st.button("✦ Nudge Me", type="primary", use_container_width=True)

with col_btn2:
    clear_clicked = st.button("Clear", use_container_width=True)

if clear_clicked:
    st.session_state.input_area = ""
    st.session_state.extracted_tasks = None
    st.session_state.status_error = None
    st.rerun()

# Processing Trigger
if nudge_clicked:
    clean_text = user_text.strip()
    if not clean_text:
        st.session_state.status_error = "Write something first."
        st.session_state.extracted_tasks = None
    elif not ollama_ok:
        st.session_state.status_error = "Nudge can't connect to Ollama. Make sure Ollama is running locally.\n\nRun in terminal: `ollama serve`"
        st.session_state.extracted_tasks = None
    elif not detected_model:
        st.session_state.status_error = f"The configured Gemma model isn't available locally. Expected: `{ai.DEFAULT_GEMMA_MODEL}`"
        st.session_state.extracted_tasks = None
    else:
        st.session_state.status_error = None
        with st.spinner("Extracting actionable tasks locally with Gemma..."):
            success, msg, tasks = ai.extract_tasks(clean_text, model_name=detected_model)
            if not success:
                st.session_state.status_error = msg
                st.session_state.extracted_tasks = None
            else:
                st.session_state.extracted_tasks = tasks
                st.session_state.last_processed_text = clean_text
                if not tasks:
                    st.session_state.status_error = "I couldn't find a clear action in that note."

# Error / Empty States
if st.session_state.status_error:
    if st.session_state.status_error == "Write something first.":
        st.info("Write something first.")
    elif st.session_state.status_error == "I couldn't find a clear action in that note.":
        st.info("I couldn't find a clear action in that note.")
    else:
        st.error(st.session_state.status_error)

# Results Screen
if st.session_state.extracted_tasks is not None and len(st.session_state.extracted_tasks) > 0:
    tasks = st.session_state.extracted_tasks
    count = len(tasks)
    count_str = f"{count} task found" if count == 1 else f"{count} tasks found"

    st.markdown(
        f"""
<div class="section-headline">
    <span class="section-count">{count_str}</span>
    <span class="section-badge-group">TODAY / UPCOMING</span>
</div>
""",
        unsafe_allow_html=True,
    )

    priority_icons = {
        "high": "🔴",
        "medium": "🟡",
        "low": "🟢",
    }

    # Render Task Cards
    for idx, t in enumerate(tasks):
        pri = t.get("priority", "medium")
        cat = t.get("category", "other")
        icon = priority_icons.get(pri, "🟡")
        human_date = t.get("human_date", "No deadline")

        st.markdown(
            f"""
<div class="task-card">
    <div class="task-title">
        <span>{icon}</span> {t.get('title')}
    </div>
    <div class="task-meta-row">
        <span><strong>{human_date}</strong></span>
        <span class="meta-separator">·</span>
        <span class="badge badge-priority-{pri}">{pri.upper()}</span>
        <span class="meta-separator">·</span>
        <span class="badge badge-category">{cat.upper()}</span>
    </div>
</div>
""",
            unsafe_allow_html=True,
        )

    # Section 10: "WHY NUDGE?" SECTION
    with st.expander("Why did Nudge create these tasks?", expanded=False):
        for idx, t in enumerate(tasks, 1):
            st.markdown(f"**Task {idx}: {t.get('title')}**")
            bullets = t.get("evidence", {}).get("explanation_bullets", [])
            if bullets:
                for b in bullets:
                    st.markdown(f"- {b}")
            else:
                # Fallback evidence explanation
                st.markdown(f"- Date: {t.get('human_date')}")
                st.markdown(f"- Priority: {t.get('priority')}")
                st.markdown(f"- Category: {t.get('category')}")
            if idx < len(tasks):
                st.write("")

    # Clean action bar
    col_dl1, col_dl2 = st.columns([1, 1])
    with col_dl1:
        # JSON export for integration or testing
        json_str = json.dumps({"tasks": tasks}, indent=2)
        st.download_button(
            label="Download JSON",
            data=json_str,
            file_name="nudge_tasks.json",
            mime="application/json",
            use_container_width=True,
        )
    with col_dl2:
        if st.button("New Note", use_container_width=True):
            st.session_state.input_area = ""
            st.session_state.extracted_tasks = None
            st.session_state.status_error = None
            st.rerun()

# Subtly placed Local AI / Hacktoberfest Story Footer
st.markdown(
    """
<div class="local-footer">
    <strong>✦ Nudge</strong> — Built for the <em>Hacktoberfest 2026 "Build for a Friend"</em> challenge.<br>
    Runs 100% on device using open-weight Gemma 3 via Ollama. No cloud APIs, no tracking, complete privacy.
</div>
""",
    unsafe_allow_html=True,
)
