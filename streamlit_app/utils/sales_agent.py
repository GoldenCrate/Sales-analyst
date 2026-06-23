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
