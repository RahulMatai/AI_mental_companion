"""Pocket Therapist — Streamlit entry point.

Design philosophy:
- Three screens. No chrome. No clutter.
- Typography does the heavy lifting: Fraunces (serif) for emotional weight,
  Inter Tight (sans) for clarity, JetBrains Mono for metadata.
- Color discipline: warm dark base, cream text, single amber accent used
  sparingly for emphasis and focus.
- Custom HTML for messages — Streamlit's default st.chat_message renders
  ugly avatar boxes we can't fully suppress, so we render bubbles ourselves
  and only use st.empty() for the streaming placeholder.

Run locally:
    streamlit run app.py
"""
import html
import random
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from core import conversation, storage
from core.prompts import OPENERS
from utils.logger import get_logger

load_dotenv()
logger = get_logger(__name__)


# ----------------------------- Page setup -----------------------------------

st.set_page_config(
    page_title="Pocket Therapist",
    page_icon="🌙",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={},
)


CUSTOM_CSS = """
<style>
/* ── Kill Streamlit chrome ─────────────────────────────────────── */
#MainMenu, footer, header[data-testid="stHeader"] { display: none !important; }
[data-testid="stToolbar"], [data-testid="stDecoration"] { display: none !important; }
[data-testid="stStatusWidget"], .stDeployButton { display: none !important; }
[data-testid="InputInstructions"] { display: none !important; }
.viewerBadge_container__1QSob { display: none !important; }

/* ── Fonts ─────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..600;1,9..144,300..500&family=Inter+Tight:wght@300;400;500;600&family=JetBrains+Mono:wght@400&display=swap');

/* ── Design tokens ─────────────────────────────────────────────── */
:root {
  --bg:          #0a0908;
  --surface:     #161412;
  --surface-2:   #1f1c18;
  --border:      #2a2620;
  --text:        #ede9e0;
  --text-muted:  #8a8378;
  --text-dim:    #5c574e;
  --accent:      #d4a574;
  --accent-soft: rgba(212, 165, 116, 0.12);
  --serif:       'Fraunces', Georgia, serif;
  --sans:        'Inter Tight', system-ui, sans-serif;
  --mono:        'JetBrains Mono', ui-monospace, monospace;
}

/* ── Base ──────────────────────────────────────────────────────── */
html, body, .stApp, [data-testid="stAppViewContainer"] {
  background: var(--bg) !important;
  color: var(--text);
  font-family: var(--sans);
  -webkit-font-smoothing: antialiased;
}

.block-container {
  padding-top: 4.5rem !important;
  padding-bottom: 9rem !important;
  max-width: 640px !important;
}

/* ── Typography primitives ─────────────────────────────────────── */
.eyebrow {
  font-family: var(--mono);
  font-size: 0.72rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-bottom: 1.5rem;
}

.eyebrow .dot { color: var(--accent); margin-right: 0.5rem; }

.greeting {
  font-family: var(--serif);
  font-weight: 300;
  font-size: 3.2rem;
  letter-spacing: -0.025em;
  line-height: 1.05;
  color: var(--text);
  margin: 0 0 0.6rem 0;
}

.greeting em {
  font-style: italic;
  color: var(--accent);
  font-weight: 300;
}

.subtitle {
  font-family: var(--serif);
  font-style: italic;
  font-weight: 300;
  font-size: 1.18rem;
  color: var(--text-muted);
  line-height: 1.5;
  margin-bottom: 3.5rem;
}

.section-title {
  font-family: var(--serif);
  font-weight: 300;
  font-size: 2rem;
  letter-spacing: -0.015em;
  color: var(--text);
  margin: 0.5rem 0 2rem 0;
}

/* ── Buttons ───────────────────────────────────────────────────── */
.stButton > button {
  font-family: var(--sans) !important;
  font-weight: 500 !important;
  font-size: 0.95rem !important;
  letter-spacing: 0.005em !important;
  background: transparent !important;
  color: var(--text) !important;
  border: 1px solid var(--border) !important;
  border-radius: 999px !important;
  padding: 0.75rem 1.5rem !important;
  transition: all 0.22s ease !important;
  box-shadow: none !important;
  width: 100%;
}

.stButton > button:hover {
  background: var(--surface) !important;
  border-color: var(--accent) !important;
  color: var(--text) !important;
}

.stButton > button:focus:not(:active) {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px var(--accent-soft) !important;
}

.stButton > button[kind="primary"] {
  background: var(--accent) !important;
  color: #1a1410 !important;
  border-color: var(--accent) !important;
  font-weight: 600 !important;
}

.stButton > button[kind="primary"]:hover {
  background: #e0b485 !important;
  border-color: #e0b485 !important;
  transform: translateY(-1px);
}

/* ── Quiet link button (for "Past sessions") ───────────────────── */
.stButton.quiet > button {
  border: none !important;
  background: transparent !important;
  color: var(--text-muted) !important;
  font-weight: 400 !important;
  font-size: 0.88rem !important;
  font-style: italic;
  font-family: var(--serif) !important;
  padding: 0.5rem !important;
}

.stButton.quiet > button:hover {
  color: var(--accent) !important;
  background: transparent !important;
  border: none !important;
}

/* ── Chat messages (custom HTML) ───────────────────────────────── */
.msg-row {
  display: flex;
  margin-bottom: 1.6rem;
  animation: fade-up 0.4s cubic-bezier(0.2, 0.7, 0.2, 1);
}

@keyframes fade-up {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.msg-ai   { justify-content: flex-start; }
.msg-user { justify-content: flex-end; }

.bubble {
  max-width: 86%;
  font-size: 1.02rem;
  line-height: 1.6;
}

.bubble-ai {
  font-family: var(--serif);
  font-weight: 300;
  font-size: 1.15rem;
  line-height: 1.55;
  color: var(--text);
  letter-spacing: 0.005em;
  padding: 0.2rem 0 0.2rem 1.2rem;
  border-left: 2px solid var(--accent);
}

.bubble-user {
  background: var(--surface);
  color: var(--text);
  font-family: var(--sans);
  font-weight: 400;
  padding: 0.85rem 1.15rem;
  border-radius: 18px 18px 6px 18px;
}

.cursor {
  display: inline-block;
  width: 0.45em;
  margin-left: 2px;
  color: var(--accent);
  animation: blink 1.05s steps(2) infinite;
}

@keyframes blink { 50% { opacity: 0; } }

/* ── Chat input ────────────────────────────────────────────────── */
/* Force the WHOLE bottom strip to match the theme. Streamlit wraps the
   chat input in several containers that default to white — kill them all. */
[data-testid="stBottom"],
[data-testid="stBottomBlockContainer"],
[data-testid="stBottom"] > div,
[data-testid="stBottom"] > div > div,
.stBottom, .stBottomBlockContainer,
section.main > div:last-child,
[data-testid="stChatInput"] {
  background: var(--bg) !important;
  background-color: var(--bg) !important;
  border: none !important;
}

[data-testid="stChatInput"] > div {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 16px !important;
  box-shadow: none !important;
  transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}

/* Hide everything inside the chat input that isn't the submit button —
   this kills the green robot/voice icon Streamlit adds by default. */
[data-testid="stChatInput"] button:not([data-testid="stChatInputSubmitButton"]) {
  display: none !important;
}

/* Hide the floating sparkle / suggestion / voice buttons that sit
   below or beside the input. We cast a wide net since Streamlit
   versions name these differently. */
[data-testid*="ChatInputSuggest"],
[data-testid="stChatInputAcceptSuggestion"],
[data-testid="stChatInputVoiceRecord"],
[data-testid="stChatInputVoiceRecordButton"],
[data-testid*="stChatInputImagine"],
[data-testid*="stImagine"],
button[title*="Voice" i],
button[title*="Record" i],
button[title*="Imagine" i],
button[aria-label*="Voice" i],
button[aria-label*="Imagine" i] {
  display: none !important;
}

[data-testid="stChatInput"] > div:focus-within {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px var(--accent-soft) !important;
}

[data-testid="stChatInput"] textarea {
  background: transparent !important;
  color: var(--text) !important;
  font-family: var(--sans) !important;
  font-size: 1rem !important;
  caret-color: var(--accent) !important;
}

[data-testid="stChatInput"] textarea::placeholder {
  color: var(--text-dim) !important;
  font-style: italic;
  opacity: 1;
}

[data-testid="stChatInputSubmitButton"] svg { color: var(--accent) !important; }
[data-testid="stChatInputSubmitButton"]:hover { background: var(--accent-soft) !important; }

/* ── History cards ─────────────────────────────────────────────── */
.history-card {
  padding: 1.3rem 1.4rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  margin-bottom: 0.85rem;
  transition: border-color 0.2s ease, transform 0.2s ease;
}

.history-card:hover {
  border-color: var(--accent);
  transform: translateX(2px);
}

.history-date {
  font-family: var(--mono);
  font-size: 0.7rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-bottom: 0.55rem;
}

.history-summary {
  font-family: var(--serif);
  font-style: italic;
  font-weight: 300;
  font-size: 1.08rem;
  color: var(--text);
  line-height: 1.5;
  letter-spacing: 0.005em;
}

/* ── Empty state ───────────────────────────────────────────────── */
.empty-state {
  text-align: center;
  padding: 4rem 0 2rem;
  font-family: var(--serif);
  font-style: italic;
  color: var(--text-muted);
  font-size: 1.1rem;
  line-height: 1.5;
}

/* ── Footer (home screen only) ─────────────────────────────────── */
.footer {
  margin-top: 5rem;
  padding-top: 2rem;
  border-top: 1px solid var(--border);
  text-align: center;
  font-family: var(--mono);
  font-size: 0.7rem;
  letter-spacing: 0.06em;
  color: var(--text-dim);
  line-height: 1.9;
}

.footer .sep { margin: 0 0.6rem; color: var(--border); }

/* ── Spacing tweaks for columns inside header rows ─────────────── */
[data-testid="stHorizontalBlock"] { gap: 0.5rem !important; }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ----------------------------- Helpers --------------------------------------

def _time_greeting() -> tuple[str, str]:
    """Return (prefix, accent_word) so we can italicize the accent word."""
    hour = datetime.now().hour
    if hour < 5:
        return ("It's", "late")
    if hour < 12:
        return ("Good", "morning")
    if hour < 17:
        return ("Good", "afternoon")
    if hour < 21:
        return ("Good", "evening")
    return ("It's", "late")


def _escape(text: str) -> str:
    return html.escape(text).replace("\n", "<br>")


def render_message(role: str, content: str, streaming: bool = False) -> str:
    safe = _escape(content)
    cursor = '<span class="cursor">▍</span>' if streaming else ""
    if role == "assistant":
        return (
            f'<div class="msg-row msg-ai">'
            f'<div class="bubble bubble-ai">{safe}{cursor}</div>'
            f'</div>'
        )
    return (
        f'<div class="msg-row msg-user">'
        f'<div class="bubble bubble-user">{safe}</div>'
        f'</div>'
    )


def _init_state() -> None:
    storage.init_db()
    st.session_state.setdefault("session_id", None)
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("view", "home")


def _start_new_chat() -> None:
    st.session_state.session_id = storage.new_session()
    opener = random.choice(OPENERS)
    st.session_state.messages = [{"role": "assistant", "content": opener}]
    storage.save_message(st.session_state.session_id, "assistant", opener)
    st.session_state.view = "chat"


def _end_chat() -> None:
    sid = st.session_state.session_id
    if sid and st.session_state.messages:
        user_msgs = [m for m in st.session_state.messages if m["role"] == "user"]
        summary = (
            conversation.summarize_session(st.session_state.messages)
            if user_msgs else None
        )
        storage.close_session(sid, summary)
    st.session_state.session_id = None
    st.session_state.messages = []
    st.session_state.view = "home"


# ----------------------------- Views ----------------------------------------

def render_home() -> None:
    prefix, accent_word = _time_greeting()

    st.markdown(
        '<div class="eyebrow"><span class="dot">●</span>Pocket Therapist</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="greeting">{prefix} <em>{accent_word}</em>.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="subtitle">A quiet space. Five minutes. Just you.</div>',
        unsafe_allow_html=True,
    )

    if st.button("Talk", use_container_width=True, type="primary", key="talk_btn"):
        _start_new_chat()
        st.rerun()

    # Quiet secondary action
    st.markdown('<div class="stButton quiet">', unsafe_allow_html=True)
    if st.button("Past sessions  →", key="history_btn"):
        st.session_state.view = "history"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="footer">'
        'Private · stays on your device'
        '<span class="sep">·</span>'
        'Not a substitute for professional care<br>'
        'iCall 9152987821<span class="sep">·</span>Vandrevala 1860-2662-345'
        '</div>',
        unsafe_allow_html=True,
    )


def render_chat() -> None:
    # Top bar: eyebrow + End button
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(
            '<div class="eyebrow"><span class="dot">●</span>In conversation</div>',
            unsafe_allow_html=True,
        )
    with col2:
        if st.button("End", key="end_btn"):
            _end_chat()
            st.rerun()

    # Render existing message history
    for msg in st.session_state.messages:
        st.markdown(render_message(msg["role"], msg["content"]),
                    unsafe_allow_html=True)

    # Input
    user_input = st.chat_input("Type whatever's on your mind…")
    if user_input:
        # Persist + render user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        storage.save_message(st.session_state.session_id, "user", user_input)
        st.markdown(render_message("user", user_input), unsafe_allow_html=True)

        # Stream assistant reply into a placeholder
        placeholder = st.empty()
        collected = ""
        try:
            for chunk in conversation.stream_reply(st.session_state.messages):
                collected += chunk
                placeholder.markdown(
                    render_message("assistant", collected, streaming=True),
                    unsafe_allow_html=True,
                )
            placeholder.markdown(
                render_message("assistant", collected),
                unsafe_allow_html=True,
            )
        except Exception:
            logger.exception("stream_reply failed")
            collected = (
                "Something went wrong on my end. Give it a moment and try again."
            )
            placeholder.markdown(
                render_message("assistant", collected),
                unsafe_allow_html=True,
            )

        st.session_state.messages.append(
            {"role": "assistant", "content": collected}
        )
        storage.save_message(st.session_state.session_id, "assistant", collected)


def render_history() -> None:
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(
            '<div class="eyebrow"><span class="dot">●</span>Past sessions</div>',
            unsafe_allow_html=True,
        )
    with col2:
        if st.button("Back", key="back_btn"):
            st.session_state.view = "home"
            st.rerun()

    st.markdown(
        '<div class="section-title">A quiet record.</div>',
        unsafe_allow_html=True,
    )

    sessions = storage.recent_sessions(limit=20)
    if not sessions:
        st.markdown(
            '<div class="empty-state">'
            'No sessions yet.<br>Your first one is waiting.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    for s in sessions:
        started = datetime.fromisoformat(s["started_at"]).strftime(
            "%b %d, %Y  ·  %H:%M"
        )
        summary = s.get("summary") or "A quiet check-in."
        st.markdown(
            f'<div class="history-card">'
            f'<div class="history-date">{started}</div>'
            f'<div class="history-summary">{_escape(summary)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ----------------------------- Router ---------------------------------------

def main() -> None:
    _init_state()
    view = st.session_state.view
    if view == "chat":
        render_chat()
    elif view == "history":
        render_history()
    else:
        render_home()


if __name__ == "__main__":
    main()
