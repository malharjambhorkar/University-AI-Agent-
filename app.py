import csv
import html
import os
from datetime import datetime

import streamlit as st

from rag_engine import create_agent


st.set_page_config(
    page_title="VIT Pune AI Agent",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)


BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")


@st.cache_resource(show_spinner=False)
def load_agent():
    return create_agent()


@st.cache_data(show_spinner=False)
def load_feedback_rows():
    feedback_path = os.path.join(DATA_DIR, "feedback.csv")
    if not os.path.exists(feedback_path):
        return []
    with open(feedback_path, "r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def init_state():
    defaults = {
        "page": "chat",
        "messages": [
            {
                "role": "assistant",
                "content": "Welcome to the VIT Pune AI Agent. Ask about hostel rules, exam dates, fees, placements, feedback insights, or reports.",
            }
        ],
        "agent_ready": False,
        "last_report": "",
        "last_feedback_summary": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def sync_agent_status(agent) -> None:
    st.session_state.agent_ready = bool(agent.diagnostics.llm_available or agent.diagnostics.retrieval_available)


def escape_text(text: str) -> str:
    return html.escape(text).replace("\n", "<br>")


def sentiment_counts(rows):
    counts = {"Positive": 0, "Negative": 0, "Neutral": 0}
    for row in rows:
        sentiment = row.get("Sentiment", "").title()
        if sentiment in counts:
            counts[sentiment] += 1
    return counts


def quick_submit(query: str):
    st.session_state.messages.append({"role": "user", "content": query})
    try:
        agent = load_agent()
        sync_agent_status(agent)
        response = agent.run(query)
    except Exception as exc:
        st.session_state.agent_ready = False
        response = (
            "I hit an error while processing that request.\n\n"
            f"Details: {exc}\n\n"
            "If you want LLM-powered answers, make sure Ollama is running and the `llama3` model is available."
        )
    st.session_state.messages.append({"role": "assistant", "content": response})


def inject_styles():
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;700&display=swap');

:root {
    --bg: #07111f;
    --panel: rgba(11, 24, 42, 0.82);
    --panel-strong: rgba(12, 28, 48, 0.92);
    --card: rgba(255, 255, 255, 0.04);
    --card-hover: rgba(255, 255, 255, 0.07);
    --border: rgba(52, 193, 255, 0.18);
    --text: #f4f8ff;
    --muted: rgba(209, 222, 242, 0.72);
    --subtle: rgba(160, 180, 210, 0.52);
    --primary: #18c8ff;
    --primary-2: #2df0c6;
    --cyan: #56d8ff;
    --green: #46f0c2;
    --danger: #ff6f91;
    --amber: #ffcf61;
}

html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
    font-family: 'Outfit', sans-serif !important;
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 12% 18%, rgba(24, 200, 255, 0.14), transparent 26%),
        radial-gradient(circle at 82% 76%, rgba(45, 240, 198, 0.10), transparent 24%),
        linear-gradient(180deg, #07111f 0%, #050d18 100%) !important;
    color: var(--text);
}

[data-testid="stAppViewContainer"]::before {
    content: "";
    position: fixed;
    inset: 0;
    background-image:
        linear-gradient(rgba(86, 216, 255, 0.05) 1px, transparent 1px),
        linear-gradient(90deg, rgba(86, 216, 255, 0.05) 1px, transparent 1px);
    background-size: 56px 56px;
    pointer-events: none;
    opacity: 0.16;
}

[data-testid="stMainBlockContainer"] {
    padding-top: 1.2rem;
    padding-left: 1.4rem;
    padding-right: 1.4rem;
    max-width: 1400px;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(6, 14, 26, 0.98), rgba(7, 17, 31, 0.92)) !important;
    border-right: 1px solid rgba(86, 216, 255, 0.10);
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 1rem;
}

.hero {
    padding: 2rem 1rem 1.2rem 1rem;
    text-align: center;
}

.hero-badge {
    display: inline-block;
    padding: 0.45rem 1rem;
    border-radius: 999px;
    border: 1px solid rgba(86, 216, 255, 0.28);
    background: rgba(86, 216, 255, 0.10);
    color: #b9ebff;
    font-size: 0.76rem;
    letter-spacing: 0.20em;
    text-transform: uppercase;
    margin-bottom: 1rem;
}

.hero-title {
    margin: 0;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 4rem;
    line-height: 1.04;
    font-weight: 700;
    color: #dff8ff;
}

.hero-copy {
    margin-top: 0.85rem;
    color: var(--muted);
    font-size: 1.08rem;
}

.glass {
    background: linear-gradient(180deg, rgba(12, 24, 41, 0.82), rgba(9, 19, 33, 0.84));
    border: 1px solid rgba(255, 255, 255, 0.06);
    box-shadow: 0 24px 80px rgba(1, 7, 20, 0.34);
    border-radius: 24px;
    backdrop-filter: blur(18px);
}

.section {
    padding: 1.3rem;
    margin-bottom: 1rem;
}

.section-label {
    font-size: 0.72rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #8edfff;
    margin-bottom: 0.9rem;
    display: flex;
    align-items: center;
    gap: 0.65rem;
}

.section-label::after {
    content: "";
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, rgba(86, 216, 255, 0.26), transparent);
}

.stat-card {
    min-height: 120px;
    background: rgba(255, 255, 255, 0.035);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 22px;
    padding: 1.4rem 1rem;
    text-align: center;
}

.stat-value {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 2.1rem;
    color: #8cddff;
}

.stat-label {
    margin-top: 0.6rem;
    font-size: 0.74rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--subtle);
}

.quick-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    margin-bottom: 1rem;
}

.quick-pill {
    padding: 0.52rem 0.95rem;
    border-radius: 999px;
    border: 1px solid rgba(86, 216, 255, 0.20);
    background: rgba(86, 216, 255, 0.08);
    color: #d7f6ff;
    font-size: 0.86rem;
}

.feature-tile {
    text-align: center;
    padding: 0.9rem 0.5rem;
    border-radius: 18px;
    background: linear-gradient(135deg, rgba(123, 92, 255, 0.96), rgba(151, 109, 255, 0.92));
    color: white;
    font-size: 1.05rem;
    font-weight: 600;
    box-shadow: 0 14px 38px rgba(123, 92, 255, 0.22);
}

.info-list {
    color: var(--muted);
    line-height: 2;
    font-size: 0.95rem;
}

.message-list {
    display: flex;
    flex-direction: column;
    gap: 0.9rem;
    max-height: 520px;
    overflow-y: auto;
    padding-right: 0.2rem;
}

.assistant-wrap, .user-wrap {
    display: flex;
}

.assistant-wrap {
    justify-content: flex-start;
}

.user-wrap {
    justify-content: flex-end;
}

.assistant-bubble, .user-bubble {
    max-width: 85%;
    border-radius: 20px;
    padding: 0.95rem 1.05rem;
    line-height: 1.65;
    font-size: 0.95rem;
    white-space: normal;
}

.assistant-bubble {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: var(--text);
}

.user-bubble {
    background: linear-gradient(135deg, rgba(24, 200, 255, 0.92), rgba(45, 240, 198, 0.86));
    color: #062033;
    border: 1px solid rgba(255, 255, 255, 0.08);
}

.meta {
    font-size: 0.72rem;
    color: var(--subtle);
    margin-bottom: 0.3rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
}

.sidebar-brand {
    text-align: center;
    padding: 1rem 0 1.5rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 1.3rem;
}

.sidebar-brand .logo {
    font-size: 3rem;
    margin-bottom: 0.5rem;
}

.sidebar-brand .name {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.35rem;
    font-weight: 700;
    color: var(--text);
}

.sidebar-brand .sub {
    color: var(--subtle);
    font-size: 0.74rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
}

.status-online, .status-offline {
    padding: 0.8rem 0.95rem;
    border-radius: 14px;
    font-size: 0.85rem;
}

.status-online {
    color: #b8ffea;
    border: 1px solid rgba(45, 240, 198, 0.24);
    background: rgba(8, 58, 52, 0.36);
}

.status-offline {
    color: #ffd873;
    border: 1px solid rgba(255, 207, 97, 0.28);
    background: rgba(82, 61, 10, 0.25);
}

.filter-caption {
    color: var(--subtle);
    font-size: 0.8rem;
    margin-top: -0.3rem;
    margin-bottom: 0.9rem;
}

.feedback-card {
    padding: 1rem 1rem;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}

.feedback-meta {
    color: var(--subtle);
    font-size: 0.76rem;
    margin-bottom: 0.35rem;
}

.feedback-text {
    color: var(--text);
    font-size: 0.92rem;
    line-height: 1.6;
}

.badge {
    display: inline-block;
    padding: 0.25rem 0.7rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    margin-top: 0.55rem;
    margin-right: 0.4rem;
}

.badge-positive {
    color: #57f4b8;
    background: rgba(30, 231, 168, 0.12);
    border: 1px solid rgba(30, 231, 168, 0.22);
}

.badge-negative {
    color: #ff8cab;
    background: rgba(255, 111, 145, 0.12);
    border: 1px solid rgba(255, 111, 145, 0.22);
}

.badge-neutral {
    color: #ffd873;
    background: rgba(255, 207, 97, 0.12);
    border: 1px solid rgba(255, 207, 97, 0.22);
}

.report-box {
    white-space: pre-wrap;
    line-height: 1.8;
    color: var(--text);
    font-size: 0.95rem;
}

.stTextInput input, .stSelectbox [data-baseweb="select"] > div {
    background: rgba(255,255,255,0.045) !important;
    color: var(--text) !important;
    border-radius: 18px !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
}

.stButton > button {
    border-radius: 18px !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    background: linear-gradient(135deg, rgba(24, 200, 255, 0.96), rgba(45, 240, 198, 0.92)) !important;
    color: #07111f !important;
    font-weight: 600 !important;
    min-height: 2.8rem !important;
    box-shadow: 0 12px 32px rgba(24, 200, 255, 0.16) !important;
}

.stButton > button:hover {
    border-color: rgba(255,255,255,0.18) !important;
}

div[data-testid="stHorizontalBlock"] > div:has(.stat-card) {
    width: 100%;
}

.welcome-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.9rem;
}

.welcome-card {
    padding: 1rem;
    border-radius: 20px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
}

.welcome-title {
    font-size: 0.84rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #9ce7ff;
    margin-bottom: 0.55rem;
}

.welcome-copy, .soft-list {
    color: var(--muted);
    line-height: 1.8;
    font-size: 0.94rem;
}

@media (max-width: 900px) {
    .welcome-grid {
        grid-template-columns: 1fr;
    }

    .hero-title {
        font-size: 2.8rem;
    }
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar():
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <div class="logo">🎓</div>
                <div class="name">VIT Pune AI</div>
                <div class="sub">Campus Assistant</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        nav_items = [
            ("chat", "AI Chat"),
            ("feedback", "Feedback"),
            ("reports", "Reports"),
            ("about", "Guide"),
        ]
        for key, label in nav_items:
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.page = key
                st.rerun()

        st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)

        if st.button("Initialize Agent", use_container_width=True):
            with st.spinner("Initializing AI agent..."):
                agent = load_agent()
                sync_agent_status(agent)
            st.rerun()

        if st.session_state.agent_ready:
            agent = load_agent()
            if agent.diagnostics.llm_available:
                st.markdown("<div class='status-online'>● Agent online with Ollama and local knowledge base</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='status-online'>● Agent ready in local fallback mode without Ollama</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                "<div class='status-offline'>● Agent not initialized yet. The app can still load, but Ollama-backed answers need setup.</div>",
                unsafe_allow_html=True,
            )

        if st.button("Clear Chat", use_container_width=True):
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": "Chat cleared. Ask a new university question whenever you're ready.",
                }
            ]
            st.rerun()

        st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
        st.caption("Ask questions, review feedback, and generate campus reports.")
        st.caption(datetime.now().strftime("%d %b %Y"))


def render_hero(feedback_rows):
    stats = [
        ("24/7", "Ready To Help"),
        (f"{len(feedback_rows)}+", "Student Voices"),
        ("Chat", "Natural Answers"),
        ("Reports", "Instant Insights"),
        ("Fast", "Smooth Experience"),
    ]

    st.markdown(
        """
        <div class="hero">
            <div class="hero-badge">Campus assistant for students</div>
            <h1 class="hero-title">VIT Pune AI Agent</h1>
            <div class="hero-copy">Ask about campus life, deadlines, placements, hostel rules, or student feedback and get a clean answer without digging through documents.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(5)
    for col, (value, label) in zip(cols, stats):
        with col:
            st.markdown(
                f"""
                <div class="stat-card">
                    <div class="stat-value">{value}</div>
                    <div class="stat-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)


def render_chat_page(feedback_rows):
    render_hero(feedback_rows)
    col_main, col_side = st.columns([4.5, 2.2], gap="large")

    with col_main:
        st.markdown('<div class="glass section">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Start Here</div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="welcome-grid">
                <div class="welcome-card">
                    <div class="welcome-title">Ask Naturally</div>
                    <div class="welcome-copy">Type full questions the same way you would ask a real assistant. No special format is needed.</div>
                </div>
                <div class="welcome-card">
                    <div class="welcome-title">Use Shortcuts</div>
                    <div class="welcome-copy">Tap a quick prompt for common student needs like hostel info, exams, placements, and reports.</div>
                </div>
                <div class="welcome-card">
                    <div class="welcome-title">Stay Focused</div>
                    <div class="welcome-copy">Use one topic at a time for cleaner answers, especially when generating reports or summaries.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">Quick Prompts</div>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="quick-pills">
                <span class="quick-pill">What are the hostel rules?</span>
                <span class="quick-pill">When is the Tech Fest?</span>
                <span class="quick-pill">What are the exam dates?</span>
                <span class="quick-pill">Top placement companies?</span>
                <span class="quick-pill">Library timings?</span>
                <span class="quick-pill">Summarize all feedback</span>
                <span class="quick-pill">Generate placement report</span>
                <span class="quick-pill">What is the fee structure?</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        quick_buttons = [
            "Hostel Rules",
            "Tech Fest",
            "Exams",
            "Placements",
        ]
        quick_queries = {
            "Hostel Rules": "What are the hostel rules?",
            "Tech Fest": "When is the Tech Fest Avishkar?",
            "Exams": "What are the exam dates?",
            "Placements": "Tell me about placements and top recruiting companies.",
        }
        quick_cols = st.columns(4)
        for col, label in zip(quick_cols, quick_buttons):
            with col:
                if st.button(label, key=f"quick_{label}", use_container_width=True):
                    quick_submit(quick_queries[label])
                    st.rerun()

        st.markdown("<div style='height:0.8rem;'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">Conversation</div>', unsafe_allow_html=True)

        chat_html = ['<div class="message-list">']
        for message in st.session_state.messages:
            bubble = "assistant-bubble" if message["role"] == "assistant" else "user-bubble"
            wrapper = "assistant-wrap" if message["role"] == "assistant" else "user-wrap"
            meta = "VIT AI Agent" if message["role"] == "assistant" else "You"
            chat_html.append(
                f'<div class="{wrapper}">'
                f'<div>'
                f'<div class="meta">{meta}</div>'
                f'<div class="{bubble}">{escape_text(message["content"])}</div>'
                f'</div>'
                f'</div>'
            )
        chat_html.append("</div>")
        st.markdown("".join(chat_html), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="glass section">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Ask Anything</div>', unsafe_allow_html=True)
        with st.form("chat_form", clear_on_submit=True):
            input_col, button_col = st.columns([5, 1])
            with input_col:
                user_query = st.text_input(
                    "Ask a question",
                    placeholder="Ask about campus life, academics, deadlines, reports, or student feedback...",
                    label_visibility="collapsed",
                )
            with button_col:
                submitted = st.form_submit_button("Send", use_container_width=True)

        if submitted and user_query.strip():
            quick_submit(user_query.strip())
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_side:
        st.markdown(
            """
            <div class="glass section">
                <div class="section-label">What Can I Ask?</div>
                <div class="info-list">
                    🏠 Hostel rules and timings<br>
                    📚 Course and department info<br>
                    🗓 Exam and event dates<br>
                    💰 Fee structure<br>
                    💼 Placement details<br>
                    📊 Feedback summaries<br>
                    📋 Generate reports<br>
                    📞 Contact information
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        counts = sentiment_counts(feedback_rows)
        st.markdown(
            f"""
            <div class="glass section">
                <div class="section-label">Student Mood Snapshot</div>
                <div class="soft-list">
                    Positive feedback: <strong>{counts['Positive']}</strong><br>
                    Negative feedback: <strong>{counts['Negative']}</strong><br>
                    Neutral feedback: <strong>{counts['Neutral']}</strong><br>
                    Best for: quick answers, summaries, and guided reports
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="glass section">
                <div class="section-label">Tips</div>
                <div class="soft-list">
                    Ask follow-up questions to refine an answer instead of starting over.<br>
                    Use the Feedback page when you want filtered student opinions first.<br>
                    Keep report topics narrow for stronger, more relevant summaries.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_feedback_page(feedback_rows):
    st.markdown('<div class="section-label">Student Feedback Dashboard</div>', unsafe_allow_html=True)

    counts = sentiment_counts(feedback_rows)
    cols = st.columns(4)
    for col, pair in zip(
        cols,
        [
            (counts["Positive"], "Positive"),
            (counts["Negative"], "Negative"),
            (counts["Neutral"], "Neutral"),
            (len(feedback_rows), "Total"),
        ],
    ):
        with col:
            st.markdown(
                f"""
                <div class="stat-card">
                    <div class="stat-value">{pair[0]}</div>
                    <div class="stat-label">{pair[1]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    categories = ["All"] + sorted({row.get("Category", "") for row in feedback_rows if row.get("Category")})
    col1, col2 = st.columns(2)
    with col1:
        category = st.selectbox("Category", categories)
    with col2:
        sentiment = st.selectbox("Sentiment", ["All", "Positive", "Negative", "Neutral"])

    filtered = feedback_rows
    if category != "All":
        filtered = [row for row in filtered if row.get("Category") == category]
    if sentiment != "All":
        filtered = [row for row in filtered if row.get("Sentiment", "").title() == sentiment]

    st.markdown(
        f"<div class='filter-caption'>Showing {len(filtered)} feedback records after filtering.</div>",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="glass section">', unsafe_allow_html=True)
    for row in filtered:
        badge_class = f"badge-{row.get('Sentiment', '').lower()}"
        st.markdown(
            f"""
            <div class="feedback-card">
                <div class="feedback-meta">
                    ID {escape_text(row.get('StudentID', ''))} · {escape_text(row.get('Department', ''))} · Year {escape_text(row.get('Year', ''))}
                </div>
                <div class="feedback-text">{escape_text(row.get('Feedback', ''))}</div>
                <span class="badge {badge_class}">{escape_text(row.get('Sentiment', ''))}</span>
                <span class="badge">{escape_text(row.get('Category', ''))}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Summarize with AI Agent", use_container_width=True):
        with st.spinner("Summarizing feedback..."):
            agent = load_agent()
            sync_agent_status(agent)
            scope = f"{category} feedback" if category != "All" else "all feedback"
            st.session_state.last_feedback_summary = agent.summarize_feedback(scope)

    if st.session_state.last_feedback_summary:
        st.markdown(
            f"""
            <div class="glass section">
                <div class="section-label">AI Summary</div>
                <div class="report-box">{escape_text(st.session_state.last_feedback_summary)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_reports_page():
    st.markdown('<div class="section-label">Report Generator</div>', unsafe_allow_html=True)

    default_topics = [
        "Overall Student Satisfaction",
        "Hostel Facilities",
        "Academic Performance and Feedback",
        "Placement and Career Services",
        "Library and Learning Resources",
        "Canteen and Food Services",
        "Events and Extracurricular Activities",
        "Faculty Feedback Summary",
    ]

    st.markdown('<div class="glass section">', unsafe_allow_html=True)
    topic = st.selectbox("Select topic", default_topics)
    custom_topic = st.text_input("Or enter a custom topic", placeholder="e.g. WiFi infrastructure, Security, Scholarships")
    final_topic = custom_topic.strip() if custom_topic.strip() else topic
    st.markdown(
        f"<div class='filter-caption'>Report target: <strong>{escape_text(final_topic)}</strong></div>",
        unsafe_allow_html=True,
    )
    if st.button("Generate AI Report", use_container_width=True):
        with st.spinner("Generating report..."):
            agent = load_agent()
            sync_agent_status(agent)
            st.session_state.last_report = agent.generate_report(final_topic)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.last_report:
        st.markdown(
            f"""
            <div class="glass section">
                <div class="section-label">Generated Report</div>
                <div class="report-box">{escape_text(st.session_state.last_report)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_about_page(feedback_rows):
    counts = sentiment_counts(feedback_rows)
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(
            f"""
            <div class="glass section">
                <div class="section-label">What This Assistant Does</div>
                <div class="soft-list">
                    Helps students find fast answers without searching multiple files.<br>
                    Pulls together university information, deadlines, and student feedback.<br>
                    Supports quick campus questions as well as structured report generation.<br>
                    Keeps the experience simple even when advanced AI features are unavailable.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="glass section">
                <div class="section-label">Campus Snapshot</div>
                <div class="soft-list">
                    Feedback records available: <strong>{len(feedback_rows)}</strong><br>
                    Positive responses: <strong>{counts['Positive']}</strong><br>
                    Negative responses: <strong>{counts['Negative']}</strong><br>
                    Neutral responses: <strong>{counts['Neutral']}</strong><br>
                    Main sources include campus information, deadlines, and student feedback
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            """
            <div class="glass section">
                <div class="section-label">Best Ways To Use It</div>
                <div class="soft-list">
                    Start in chat for direct answers about exams, fees, rules, and contacts.<br>
                    Open Feedback to explore student comments by category and sentiment.<br>
                    Use Reports when you want a clear summary on one campus topic.<br>
                    Ask narrower questions for sharper, more relevant answers.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="glass section">
                <div class="section-label">What You Can Ask</div>
                <div class="soft-list">
                    Hostel timings, rules, services, and common concerns<br>
                    Department information, exams, events, and important dates<br>
                    Placement details and student sentiment around career support<br>
                    Quick feedback summaries and topic-based campus reports
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


init_state()
inject_styles()
feedback_rows = load_feedback_rows()
sync_agent_status(load_agent())
render_sidebar()

if st.session_state.page == "chat":
    render_chat_page(feedback_rows)
elif st.session_state.page == "feedback":
    render_feedback_page(feedback_rows)
elif st.session_state.page == "reports":
    render_reports_page()
else:
    render_about_page(feedback_rows)
