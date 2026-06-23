# AI Workflow Agent — Design Spec

**Date:** 2026-06-23
**Author:** Leo Chan
**Project:** Sales-analyst (new Page 5 added to the existing NA VAS app)
**Target role:** AI Workflow / Solutions Analyst, Value Added Services — Visa Inc. (NA VAS)

---

## 1. Purpose

Add a fifth page to the NA VAS Sales-analyst app: an **AI Workflow Agent** — a
Claude-powered conversational assistant that answers natural-language questions
about the pipeline, deals, and time-to-revenue data with **data-grounded answers
and insights**, plus a one-click **"Generate executive summary"** automation that
writes a QBR-style digest from the live data.

This fills the one capability the project currently only simulates: the existing
Page 4 "AI Insight Engine" is rule-based, not a true AI agent. The new page
demonstrates the role's headline requirement — *"design and build AI-powered
agents, automations, and workflows"* — and mirrors the production AI data agent
Leo built for the partnerships team at CouponFollow.

## 2. Job-posting alignment

| JD requirement | How this feature demonstrates it |
|---|---|
| "Design and build AI-powered agents" | The conversational agent over sales data |
| "Automate recurring reporting… summarization" | One-click executive-summary generator |
| "Leverage modern AI tools to support analysis" | Claude grounded in the dashboard's computed metrics |
| "Storytelling & executive communication" | Auto-summary produces an exec-ready narrative |
| "Analyze sales, pipeline, revenue, performance data" | Existing Pages 1–4 + the agent's grounded context |
| Post-sales intake / time-to-revenue | Existing Page 3 + agent can answer cycle-time/bottleneck questions |

## 3. Architecture (follows the project's existing patterns)

- **`streamlit_app/utils/sales_agent.py`** — pure-ish helpers + the LLM calls:
  - `build_context(pipeline_df, deals_df, recommendations) -> str` — assembles a
    compact, **computed** grounding summary (pipeline by product/segment, win rates,
    avg days-to-close, MoM growth, deal-health bands, post-sale time-to-revenue and
    bottlenecks, and the current stalled-deal flags). Pure and deterministic.
  - `build_user_prompt(question, context) -> str` — wraps the user's question with
    the grounding context. Pure.
  - `ask_agent(question, context, client=None) -> str` — calls Claude (or an
    injected fake client in tests) and returns the grounded answer.
  - `generate_exec_summary(context, client=None) -> str` — calls Claude with a
    QBR-summary system prompt and returns the digest.
- **`streamlit_app/pages/5_ai_workflow_agent.py`** — `st.chat_input` /
  `st.chat_message` chat UI with session-scoped history, plus a
  "Generate executive summary" button.
- Reuses `utils/data_loader.py` (`load_pipeline_monthly`, `load_deals`),
  `utils/deal_health.py` (`compute_deal_health`), and
  `utils/ai_recommendations.py` (`compute_ai_recommendations`) to build the context.
- **LLM:** Anthropic Claude (`claude-haiku-4-5`), reusing Leo's existing API key.
- **Grounding:** answers are built only from real computed figures passed in the
  context — no code execution, no hallucinated numbers.

## 4. New plumbing this project needs

- **`requirements.txt`** — `streamlit`, `altair`, `pandas`, `anthropic`, `pytest`
  (needed so Streamlit Cloud installs `anthropic`; the other deps ship with Streamlit
  but are pinned here for reproducibility).
- **API key handling** — read `ANTHROPIC_API_KEY` from `st.secrets` and bridge it to
  an environment variable for the (Streamlit-free) agent module, the same pattern used
  in Visa-Security-Code-Reviewer. Add `.env.example`; ensure `.env` is gitignored.
- **Model id** configurable via env (`CLAUDE_MODEL`, default `claude-haiku-4-5`).

## 5. Data inputs (existing schemas)

- `pipeline_monthly.csv`: month, product, acquirer_segment, deals_created, deals_won,
  pipeline_value_usd, avg_deal_size_usd, win_rate, avg_days_to_close, mom_growth.
- `deals.csv`: deal_id, product, acquirer_segment, acquirer_name, deal_value_usd, stage,
  days_in_current_stage, total_days_in_flight, is_post_sale, days_to_first_revenue.

## 6. Data flow

```
load data → build_context (computed aggregates + stalled-deal flags)
   → chat: build_user_prompt(question, context) → ask_agent → Claude → grounded answer
   → button: generate_exec_summary(context) → Claude → QBR digest
```

## 7. Testing

`tests/test_sales_agent.py` (pytest, `pythonpath = streamlit_app`):
- `build_context` includes the key computed figures (e.g., total pipeline value,
  a product win rate, count of stalled/flagged deals) — deterministic asserts on a
  small fixture.
- `build_user_prompt` contains both the question and the context.
- `ask_agent` and `generate_exec_summary` return the model's text using an injected
  fake client (mirrors the structure of the real Anthropic client) — no live API calls.

## 8. Deployment & docs

- Same Streamlit Cloud app; add the `ANTHROPIC_API_KEY` secret in the app settings.
- Update `README.md` to the modern layout (live link → screenshots → explanation →
  insights → rest) and add Page 5 (screenshot added after deploy).

## 9. Scope cuts (YAGNI)

- No text-to-SQL or code execution — grounded-context answering only.
- No cross-session chat memory (session-scoped history only); no auth.
- The JD's B2B lead-process pillar is addressed in the resume/interview, not built.
