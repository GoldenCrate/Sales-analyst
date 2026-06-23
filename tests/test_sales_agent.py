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
