# Engineering Decisions

A running log of *why* this project is built the way it is. Not what — that's in the code — but why.

## 1. The system prompt is the product

`core/prompts.py` is the single most consequential file in the repo. The difference between "AI chatbot" and "feels like a friend who gets you" is 90% prompt engineering, 10% everything else.

Specific choices:
- **"Speak like a man talks to a man"** — shifts the model away from soft, over-validating therapy-speak that puts men off in the first place.
- **2–4 sentence cap** — without it, the model defaults to essay mode, and the chat starts feeling like a textbook.
- **No markdown** — friends don't text in bullet points. The constraint forces conversational rhythm.
- **Safety is in-character, not a hard handoff** — the AI surfaces crisis resources warmly inside the conversation rather than breaking out with a sterile banner. Tonal continuity matters; sudden formality breaks trust at the exact moment trust matters most.

## 2. Streaming over blocking

Groq's `stream=True` is non-negotiable for this UX. A 3–4s wait for a full response makes it feel like talking to a server. Token-by-token streaming makes it feel like talking to someone who's thinking. Same content, completely different product.

## 3. Wrap-up nudge after N turns

The "infinite supportive chatbot" trap is real — without an off-ramp, sessions either drag on or end abruptly. We inject a system message after 6 user turns hinting the model to wrap up naturally if the conversation has done its work. The user can always keep going; we just give the model permission to land the plane.

## 4. SQLite with WAL mode, no ORM

- One file, two tables, zero migrations. WAL mode means Streamlit's frequent reruns don't fight with writes.
- UUID session IDs prevent collisions across runs.
- We deliberately do NOT use Supabase / Postgres for the MVP. Mental health data is exactly the kind of data that should default to local-first. Cloud sync is a v2 conversation.

## 5. Conversation history lives in `st.session_state`

The SQLite log is durable storage and history view. The *active* conversation lives in Streamlit's session state and is what we pass to Groq each turn. Two reasons:
- Reading the full message history from SQLite on every keystroke is wasteful.
- It separates "what the model sees" from "what we've durably written" — cleaner mental model.

## 6. Summary generation is a separate, cheap call

When a session closes we call the model with a tight prompt to produce a one-line summary for the history view. It's wrapped in `try/except` and falls back to a generic line — we never block the user on a summarization failure.

## 7. India-default crisis resources

The user (me) is in Vadodara. iCall and Vandrevala numbers are the right defaults. A `region` config could swap these later; over-engineering it now would be premature.

## 8. Three screens, not five

The earlier draft had a dashboard with mood graphs and pattern heatmaps. We cut it deliberately:
- Dashboards turn check-ins into data entry.
- Men already track too many metrics. We're trying to be the *opposite* of another tracker.
- The product is the conversation. Everything else is scaffolding.

## 9. Logging everywhere, quiet by default

`utils/logger.py` is idempotent (handlers aren't re-added on Streamlit reruns) and reads `LOG_LEVEL` from env. INFO by default, easy to flip to DEBUG. Every module gets a logger; we log session creation, model calls, and exceptions.

## 10. What we deliberately didn't do

- **No accounts.** Local only. Friction kills daily habits.
- **No notifications.** Streamlit can't push them anyway, and a real notification system would need a native app — out of scope.
- **No tone-picker in settings.** The personality is fixed for v1 so it has a clear identity. Configurable tone makes the product worse, not better, at this stage.
- **No LangChain.** Single conversation loop, single model. The Groq SDK is enough.

## Open questions for v2

- Should sessions be exportable as CSV? (Probably yes — trust through data ownership.)
- Should the model see the last 1–2 session summaries as context for continuity? (Tempting, but it changes the "fresh canvas" feel of opening the app. Need to think.)
- Voice input? (Removes the friction of typing on a phone, but Streamlit isn't the right runtime for it.)
