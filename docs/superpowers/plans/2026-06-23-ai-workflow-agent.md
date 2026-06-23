# AI Workflow Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fifth Streamlit page to the NA VAS Sales-analyst app — a Claude-powered conversational agent that answers natural-language questions about the pipeline/deals data (grounded in computed metrics) plus a one-click executive-summary automation.

**Architecture:** A `utils/sales_agent.py` module builds a deterministic, computed grounding context and wraps the Claude calls (client injectable for tests); a new Page 5 provides a chat UI + a summary button; both reuse the existing data loaders and pure functions.

**Tech Stack:** Python, Pandas, Streamlit, Anthropic Claude, Altair (existing pages), pytest.

## Global Constraints

- Tests import from `utils.*` (pytest.ini sets `pythonpath = streamlit_app`); `testpaths = tests`.
- Pure functions live in `streamlit_app/utils/`; pages run from `streamlit_app/`.
- LLM: Anthropic Claude, default model `claude-haiku-4-5` (override via `CLAUDE_MODEL` env). Reuse Leo's existing API key.
- The agent answers ONLY from the computed context passed to it — no code execution, no hallucinated numbers.
- `anthropic` is imported lazily (inside the call functions) so the module imports and tests run without the package or an API key; tests inject a fake client.
- API key read from `st.secrets["ANTHROPIC_API_KEY"]` and bridged to an env var on the page (same pattern as Visa-Security-Code-Reviewer). `.env` must be gitignored; only `.env.example` is committed.
- Existing data schemas:
  - `pipeline_monthly.csv`: month, product, acquirer_segment, deals_created, deals_won, pipeline_value_usd, avg_deal_size_usd, win_rate, avg_days_to_close, mom_growth
  - `deals.csv`: deal_id, product, acquirer_segment, acquirer_name, deal_value_usd, stage, days_in_current_stage, total_days_in_flight, is_post_sale, days_to_first_revenue
- Existing reusable funcs: `utils.data_loader.load_pipeline_monthly/load_deals`, `utils.ai_recommendations.compute_ai_recommendations(deals_df) -> list[dict]` (dicts include `severity`, `next_best_action`).

---

## File Structure

```
streamlit_app/
├── utils/
│   └── sales_agent.py                 # CREATE: build_context, build_user_prompt, ask_agent, generate_exec_summary
└── pages/
    └── 5_ai_workflow_agent.py         # CREATE: chat UI + exec-summary button
tests/
└── test_sales_agent.py                # CREATE: unit tests (fake Claude client)
requirements.txt                        # CREATE: pin deps incl. anthropic
.env.example                            # CREATE: documents env vars
.gitignore                              # MODIFY: ensure .env ignored
README.md                               # MODIFY: modern layout + Page 5
```

---

## Task 1: Agent module (context + Claude calls) + plumbing

**Files:**
- Create: `streamlit_app/utils/sales_agent.py`
- Create: `tests/test_sales_agent.py`
- Create: `requirements.txt`, `.env.example`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nothing from other new tasks. Uses `recommendations` shaped like `compute_ai_recommendations` output (list of dicts with `severity`, `next_best_action`).
- Produces:
  - `build_context(pipeline_df, deals_df, recommendations) -> str`
  - `build_user_prompt(question: str, context: str) -> str`
  - `ask_agent(question: str, context: str, client=None) -> str`
  - `generate_exec_summary(context: str, client=None) -> str`

- [ ] **Step 1: Write the failing test** — create `tests/test_sales_agent.py`:

```python
import pandas as pd

from utils.sales_agent import (
    build_context, build_user_prompt, ask_agent, generate_exec_summary,
)


def _pipeline():
    return pd.DataFrame([
        {"month": "2025-01-01", "product": "Fraud", "acquirer_segment": "Enterprise",
         "deals_created": 10, "deals_won": 5, "pipeline_value_usd": 10_000_000,
         "avg_deal_size_usd": 1_000_000, "win_rate": 0.5, "avg_days_to_close": 60, "mom_growth": 0.05},
        {"month": "2025-01-01", "product": "Tokenization", "acquirer_segment": "Mid-Market",
         "deals_created": 8, "deals_won": 2, "pipeline_value_usd": 6_000_000,
         "avg_deal_size_usd": 750_000, "win_rate": 0.3, "avg_days_to_close": 90, "mom_growth": -0.02},
    ])


def _deals():
    return pd.DataFrame([
        {"deal_id": "D1", "product": "Fraud", "acquirer_segment": "Enterprise",
         "acquirer_name": "Acme Bank", "deal_value_usd": 2_000_000, "stage": "Live",
         "days_in_current_stage": 5, "total_days_in_flight": 120, "is_post_sale": True,
         "days_to_first_revenue": 30.0},
        {"deal_id": "D2", "product": "Tokenization", "acquirer_segment": "Mid-Market",
         "acquirer_name": "Beta CU", "deal_value_usd": 500_000, "stage": "Negotiation",
         "days_in_current_stage": 8, "total_days_in_flight": 40, "is_post_sale": False,
         "days_to_first_revenue": None},
    ])


def test_build_context_includes_key_figures():
    ctx = build_context(_pipeline(), _deals(), recommendations=[])
    assert "$16.0M" in ctx     # total pipeline 10M + 6M
    assert "Fraud" in ctx
    assert "Tokenization" in ctx
    assert "50.0%" in ctx      # Fraud win rate
    assert "30" in ctx         # post-sale time-to-revenue avg days


def test_build_context_reports_flags():
    recs = [{
        "deal_id": "D9", "product": "Fraud", "acquirer_segment": "Enterprise",
        "stage": "Onboarding", "severity": "Critical", "flag_type": "post_sale_stall",
        "next_best_action": "Escalate the Acme onboarding.",
    }]
    ctx = build_context(_pipeline(), _deals(), recommendations=recs)
    assert "1 total" in ctx
    assert "Critical" in ctx
    assert "Escalate the Acme onboarding." in ctx


def test_build_user_prompt_contains_question_and_context():
    p = build_user_prompt("Which product is weakest?", "CONTEXT-BLOCK")
    assert "Which product is weakest?" in p
    assert "CONTEXT-BLOCK" in p


class _FakeContent:
    def __init__(self, text):
        self.text = text


class _FakeMessage:
    def __init__(self, text):
        self.content = [_FakeContent(text)]


class _FakeMessages:
    def __init__(self, text):
        self._text = text
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return _FakeMessage(self._text)


class _FakeClient:
    def __init__(self, text):
        self.messages = _FakeMessages(text)


def test_ask_agent_uses_client_and_returns_text():
    fake = _FakeClient("Tokenization has the weakest win rate at 30%.")
    out = ask_agent("Which product is weakest?", "ctx", client=fake)
    assert out == "Tokenization has the weakest win rate at 30%."
    sent = fake.messages.kwargs["messages"][0]["content"]
    assert "Which product is weakest?" in sent and "ctx" in sent


def test_generate_exec_summary_uses_client_and_returns_text():
    fake = _FakeClient("Q3 pipeline is healthy.")
    out = generate_exec_summary("ctx", client=fake)
    assert out == "Q3 pipeline is healthy."
    assert "ctx" in fake.messages.kwargs["messages"][0]["content"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sales_agent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'utils.sales_agent'`

- [ ] **Step 3: Write the implementation** — create `streamlit_app/utils/sales_agent.py`:

```python
import os

DEFAULT_MODEL = "claude-haiku-4-5"

SYSTEM_PROMPT_AGENT = (
    "You are a sales-operations analyst assistant for Visa's NA VAS team. "
    "Answer the user's question using ONLY the data context provided. Be concise, "
    "quantitative, and lead with the insight. If the context does not contain the "
    "answer, say so rather than guessing."
)

SYSTEM_PROMPT_SUMMARY = (
    "You are a sales-operations analyst for Visa's NA VAS team. Using ONLY the data "
    "context provided, write a concise executive QBR summary for sales leadership: "
    "pipeline health, what is working, the biggest risks/bottlenecks, and 2-3 "
    "recommended actions. Use short paragraphs and bullets; ground every claim in the "
    "numbers."
)


def build_context(pipeline_df, deals_df, recommendations) -> str:
    """Assemble a compact, computed grounding summary for the agent.

    Pure and deterministic — no I/O, no model calls.
    """
    lines = []
    total_pipeline = pipeline_df["pipeline_value_usd"].sum()
    overall_win = pipeline_df["win_rate"].mean()
    avg_dtc = pipeline_df["avg_days_to_close"].mean()
    lines.append(f"Total pipeline value: ${total_pipeline / 1e6:.1f}M")
    lines.append(f"Overall win rate: {overall_win * 100:.1f}%")
    lines.append(f"Average days to close: {avg_dtc:.0f}")

    lines.append("\nPipeline value by product:")
    by_prod_val = pipeline_df.groupby("product")["pipeline_value_usd"].sum().sort_values(ascending=False)
    for product, val in by_prod_val.items():
        lines.append(f"- {product}: ${val / 1e6:.1f}M")

    lines.append("\nWin rate by product:")
    by_prod_wr = pipeline_df.groupby("product")["win_rate"].mean().sort_values(ascending=False)
    for product, wr in by_prod_wr.items():
        lines.append(f"- {product}: {wr * 100:.1f}%")

    lines.append("\nWin rate by acquirer segment:")
    by_seg_wr = pipeline_df.groupby("acquirer_segment")["win_rate"].mean().sort_values(ascending=False)
    for seg, wr in by_seg_wr.items():
        lines.append(f"- {seg}: {wr * 100:.1f}%")

    post = deals_df[deals_df["is_post_sale"] == True]  # noqa: E712 (pandas mask)
    rev = post["days_to_first_revenue"].dropna()
    if len(rev):
        lines.append(
            f"\nPost-sale time-to-revenue: avg {rev.mean():.0f} days, "
            f"median {rev.median():.0f} days across {len(rev)} live deals"
        )

    sev_counts = {}
    for r in recommendations:
        sev_counts[r["severity"]] = sev_counts.get(r["severity"], 0) + 1
    summary = f"\nFlagged deals (AI monitoring): {len(recommendations)} total"
    if recommendations:
        summary += " — " + ", ".join(f"{k}: {v}" for k, v in sev_counts.items())
    lines.append(summary)
    for r in recommendations[:5]:
        lines.append(f"- [{r['severity']}] {r['next_best_action']}")

    return "\n".join(lines)


def build_user_prompt(question: str, context: str) -> str:
    return f"Data context:\n{context}\n\nQuestion: {question}"


def _client_or_default(client):
    if client is not None:
        return client
    from anthropic import Anthropic  # lazy import: only needed for real calls
    return Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def _call(client, system: str, user: str) -> str:
    message = client.messages.create(
        model=os.environ.get("CLAUDE_MODEL", DEFAULT_MODEL),
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return message.content[0].text


def ask_agent(question: str, context: str, client=None) -> str:
    client = _client_or_default(client)
    return _call(client, SYSTEM_PROMPT_AGENT, build_user_prompt(question, context))


def generate_exec_summary(context: str, client=None) -> str:
    client = _client_or_default(client)
    user = f"Data context:\n{context}\n\nWrite the executive summary."
    return _call(client, SYSTEM_PROMPT_SUMMARY, user)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_sales_agent.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Run the full suite (no regressions)**

Run: `pytest -q`
Expected: all pass (existing deal_health + ai_recommendations tests + 6 new).

- [ ] **Step 6: Create `requirements.txt`**

```
streamlit==1.58.0
altair==6.2.1
pandas==2.3.3
anthropic==0.111.0
pytest==8.3.3
```

(These match the versions already on Leo's machine and install cleanly on Streamlit Cloud.)

- [ ] **Step 7: Create `.env.example`**

```
ANTHROPIC_API_KEY=your-anthropic-key-here
CLAUDE_MODEL=claude-haiku-4-5
```

- [ ] **Step 8: Ensure `.env` is gitignored** — check the existing `.gitignore`; if it does not already contain a line `.env`, append:

```
# Local secrets
.env
```

Verify: `git check-ignore .env` prints `.env`.

- [ ] **Step 9: Commit**

```bash
git add streamlit_app/utils/sales_agent.py tests/test_sales_agent.py requirements.txt .env.example .gitignore
git commit -m "feat: add sales AI agent module (grounded context + Claude calls) with tests"
```

---

## Task 2: AI Workflow Agent page + README

**Files:**
- Create: `streamlit_app/pages/5_ai_workflow_agent.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `build_context`, `ask_agent`, `generate_exec_summary` (Task 1); `load_pipeline_monthly`, `load_deals`, `compute_ai_recommendations` (existing).

- [ ] **Step 1: Create the page** — create `streamlit_app/pages/5_ai_workflow_agent.py`:

```python
import os
import streamlit as st

from utils.data_loader import load_pipeline_monthly, load_deals
from utils.ai_recommendations import compute_ai_recommendations
from utils.sales_agent import build_context, ask_agent, generate_exec_summary

st.set_page_config(page_title="AI Workflow Agent", page_icon="🤖", layout="wide")

# Bridge the API key from Streamlit secrets to env vars for the agent module.
try:
    if "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
    if "CLAUDE_MODEL" in st.secrets:
        os.environ["CLAUDE_MODEL"] = st.secrets["CLAUDE_MODEL"]
except Exception:
    pass

st.title("🤖 AI Workflow Agent")
st.caption(
    "Ask questions about the NA VAS pipeline in plain English, or generate an "
    "executive summary — grounded in the dashboard's data."
)

pipeline_df = load_pipeline_monthly()
deals_df = load_deals()
recommendations = compute_ai_recommendations(deals_df)
context = build_context(pipeline_df, deals_df, recommendations)

with st.expander("What the agent can see (grounding data)"):
    st.text(context)

if st.button("Generate executive summary", type="primary"):
    with st.spinner("Generating…"):
        try:
            summary = generate_exec_summary(context)
        except Exception as exc:
            st.error(f"Could not generate summary: {exc}")
        else:
            st.markdown(summary)

st.divider()
st.subheader("Ask the agent")

if "agent_messages" not in st.session_state:
    st.session_state.agent_messages = []

for m in st.session_state.agent_messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

prompt = st.chat_input("e.g., Which product has the weakest win rate, and what should we do?")
if prompt:
    st.session_state.agent_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                answer = ask_agent(prompt, context)
            except Exception as exc:
                answer = f"Sorry — I couldn't answer that: {exc}"
            st.markdown(answer)
    st.session_state.agent_messages.append({"role": "assistant", "content": answer})

st.caption(
    "Answers are generated by Claude grounded in the figures above — for "
    "demonstration; not financial advice."
)
```

- [ ] **Step 2: Validate the page imports and the context builds on real data**

Run (from `streamlit_app/`):
```bash
python -c "import ast; ast.parse(open('pages/5_ai_workflow_agent.py', encoding='utf-8').read()); print('page parses OK')"
python -c "
import pandas as pd
from utils.ai_recommendations import compute_ai_recommendations
from utils.sales_agent import build_context
p = pd.read_csv('data/pipeline_monthly.csv', parse_dates=['month'])
d = pd.read_csv('data/deals.csv')
ctx = build_context(p, d, compute_ai_recommendations(d))
assert len(ctx) > 100 and 'Total pipeline value' in ctx
print('context OK, length', len(ctx))
print(ctx[:300])
"
```
Expected: `page parses OK` then `context OK, length <N>` and a printed context preview with real figures.

- [ ] **Step 3: Reformat the README** — replace the entire contents of `README.md` with:

```markdown
# Visa NA VAS — Sales Enablement & AI Workflow Analyst

### [Live Dashboard →](https://sales-analyst-hpecckbmvzzbhe6a5owuax.streamlit.app/)

<!-- Screenshots added after deploy: market/pipeline pages + the AI Workflow Agent -->

**A five-page NA VAS sales-enablement dashboard — pipeline analytics, velocity, post-sale time-to-revenue, automated deal monitoring, and a Claude-powered AI agent that answers pipeline questions and auto-writes executive summaries.**

---

This project models the analytical and AI-automation work of an AI Workflow / Solutions Analyst on Visa's North America Visa Acceptance Solutions (NA VAS) team. It synthesises monthly pipeline data across VAS products and acquirer segments plus individual deal snapshots to track pipeline health, velocity, and post-sale time-to-revenue — then layers on AI: automated deal monitoring with next-best-action recommendations, and a conversational **AI Workflow Agent** that answers natural-language questions about the data and generates exec-ready summaries, grounded in the dashboard's computed metrics.

## Key Insights

- **Pipeline & velocity:** The Executive Summary and Velocity pages surface win-rate trends, days-to-close, and where to focus GTM effort by product and acquirer segment.
- **Time-to-revenue:** The post-sale funnel flags stages that exceed cycle-time thresholds (bottlenecks) — the friction that delays revenue realization after a deal closes.
- **AI automation:** The AI Insight Engine auto-monitors deals and surfaces stalled ones with next-best actions; the AI Workflow Agent lets a sales leader ask questions in plain English and get grounded answers + one-click executive summaries, eliminating manual data pulls.

## Dashboard Pages

1. **Executive Pipeline Summary** — portfolio KPIs, pipeline trend, deal-health scorecard.
2. **Pipeline Velocity Model** — win rate over time, days-to-close, deal-size vs win-rate.
3. **Post-Sale Time-to-Revenue** — stage funnel, cycle-time bottleneck flagging.
4. **AI Insight Engine** — automated deal monitoring + next-best-action recommendations.
5. **AI Workflow Agent** — Claude-powered Q&A over the data + one-click executive summary.

## Tech Stack

| Layer | Tool |
|---|---|
| Data | Two synthesized CSVs — Python generator script |
| Data Processing | Pandas |
| Pure functions | `compute_deal_health`, `compute_ai_recommendations`, `build_context` (no Streamlit dependency) |
| AI Agent | Anthropic Claude (`claude-haiku-4-5`) — grounded, no code execution |
| Visualisation | Altair |
| Dashboard | Streamlit (five-page multipage app) |
| Testing | pytest |
| Deployment | Streamlit Community Cloud |

## Running locally

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY` (only needed for the AI agent page).
3. `cd streamlit_app && streamlit run 1_pipeline_summary.py`
4. Tests: `pytest` (from the project root; the agent is tested with a mocked client — no API key needed).

## Repository Structure

    .
    ├── streamlit_app/
    │   ├── 1_pipeline_summary.py
    │   ├── pages/
    │   │   ├── 2_pipeline_velocity.py
    │   │   ├── 3_time_to_revenue.py
    │   │   ├── 4_ai_insight_engine.py
    │   │   └── 5_ai_workflow_agent.py     # AI agent: Q&A + exec summary
    │   ├── utils/
    │   │   ├── data_loader.py
    │   │   ├── deal_health.py
    │   │   ├── ai_recommendations.py
    │   │   └── sales_agent.py             # grounded context + Claude calls
    │   ├── data/
    │   └── generate_data.py
    ├── tests/
    ├── requirements.txt
    ├── pytest.ini
    └── README.md
```

- [ ] **Step 4: Confirm the full test suite still passes**

Run: `pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add streamlit_app/pages/5_ai_workflow_agent.py README.md
git commit -m "feat: add AI Workflow Agent page and modernize README"
```

---

## Self-Review (completed during planning)

**Spec coverage:** Conversational agent → `ask_agent` + chat UI (Tasks 1–2). Auto-summary automation → `generate_exec_summary` + button (Tasks 1–2). Grounded context from computed metrics → `build_context` reusing existing loaders/funcs (Task 1). requirements.txt with anthropic, st.secrets→env bridge, `.env.example`, gitignored `.env` (Tasks 1–2). pytest with fake client, no live calls (Task 1). README modern layout + Page 5 (Task 2). All spec sections map to a task.

**Placeholder scan:** No TBD/TODO in code; every code step is complete; the README screenshot line is an HTML comment placeholder (screenshots are added post-deploy once captured, consistent with the other repos), not a broken image link.

**Type consistency:** `build_context(pipeline_df, deals_df, recommendations)`, `build_user_prompt(question, context)`, `ask_agent(question, context, client=None)`, `generate_exec_summary(context, client=None)` are used identically across Tasks 1–2 and the tests. `recommendations` dict keys (`severity`, `next_best_action`) match `compute_ai_recommendations`' documented output. The fake-client shape (`.messages.create(...) -> .content[0].text`) matches the real Anthropic client used in `_call`.
