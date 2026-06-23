import altair as alt
import pandas as pd
import streamlit as st

from utils.data_loader import load_pipeline_monthly
from utils.chart_style import ACCENT, CATEGORY_RANGE, GREY, insight, style

st.set_page_config(page_title="Pipeline Velocity", page_icon="📈", layout="wide")

df = load_pipeline_monthly()
products = sorted(df["product"].unique())
segments = sorted(df["acquirer_segment"].unique())

st.title("Pipeline Velocity Model")
st.caption(
    "Win rate, deal cycle time, and deal size dynamics across VAS products and acquirer segments"
)

col_f1, col_f2 = st.columns(2)
selected_product = col_f1.selectbox("Product", ["All"] + products)
selected_segments = col_f2.multiselect("Acquirer Segments", segments, default=segments)

filtered = df.copy()
if selected_product != "All":
    filtered = filtered[filtered["product"] == selected_product]
if selected_segments:
    filtered = filtered[filtered["acquirer_segment"].isin(selected_segments)]

monthly = (
    filtered.groupby(["month", "acquirer_segment"])
    .agg(
        win_rate=("win_rate", "mean"),
        avg_days_to_close=("avg_days_to_close", "mean"),
        avg_deal_size_usd=("avg_deal_size_usd", "mean"),
        pipeline_value_usd=("pipeline_value_usd", "sum"),
    )
    .reset_index()
)

sorted_months = sorted(monthly["month"].unique())
cutoff = sorted_months[-12] if len(sorted_months) >= 12 else sorted_months[0]
trend_df = monthly[monthly["month"] >= cutoff].copy()

st.divider()
st.subheader("Win Rate Over Time by Segment")

win_chart = (
    alt.Chart(trend_df)
    .mark_line(point=True)
    .encode(
        x=alt.X("month:T", title="Month", axis=alt.Axis(format="%b %Y")),
        y=alt.Y("win_rate:Q", title="Win Rate", axis=alt.Axis(format=".0%")),
        color=alt.Color("acquirer_segment:N", title="Segment",
                        scale=alt.Scale(range=CATEGORY_RANGE)),
        tooltip=[
            alt.Tooltip("month:T", title="Month", format="%B %Y"),
            "acquirer_segment:N",
            alt.Tooltip("win_rate:Q", title="Win Rate", format=".1%"),
        ],
    )
    .properties(height=280)
)
st.altair_chart(style(win_chart), use_container_width=True)
insight(
    "Watch each segment's line over time — a rising trend confirms GTM traction; "
    "a segment trending down is where win rates are slipping and need diagnosis."
)

st.divider()
st.subheader("Avg Days to Close by Segment (Last 3 Months)")

last3 = sorted_months[-3:]
days_df = (
    monthly[monthly["month"].isin(last3)]
    .groupby("acquirer_segment")
    .agg(avg_days=("avg_days_to_close", "mean"))
    .reset_index()
    .sort_values("avg_days")
)
slowest_segment = str(days_df.iloc[-1]["acquirer_segment"]) if len(days_df) else None

days_chart = (
    alt.Chart(days_df)
    .mark_bar()
    .encode(
        x=alt.X("avg_days:Q", title="Avg Days to Close"),
        y=alt.Y("acquirer_segment:N", title="Segment", sort="-x"),
        color=alt.condition(
            alt.FieldEqualPredicate(field="acquirer_segment", equal=slowest_segment),
            alt.value(ACCENT), alt.value(GREY),
        ),
        tooltip=[
            "acquirer_segment:N",
            alt.Tooltip("avg_days:Q", title="Avg Days", format=".1f"),
        ],
    )
    .properties(height=200)
)
st.altair_chart(style(days_chart), use_container_width=True)
insight(
    f"<b>{slowest_segment}</b> is the slowest to close — the longest sales cycle and "
    "the segment where shortening time-to-close would free up the most capacity."
)

st.divider()
st.subheader("Deal Size vs Win Rate by Segment")

scatter_df = (
    filtered.groupby("acquirer_segment")
    .agg(
        avg_deal_size_usd=("avg_deal_size_usd", "mean"),
        win_rate=("win_rate", "mean"),
        pipeline_value_usd=("pipeline_value_usd", "sum"),
    )
    .reset_index()
)
scatter_df["deal_size_k"] = scatter_df["avg_deal_size_usd"] / 1e3

scatter_chart = (
    alt.Chart(scatter_df)
    .mark_circle()
    .encode(
        x=alt.X("deal_size_k:Q", title="Avg Deal Size ($K)", axis=alt.Axis(format="$,.0f")),
        y=alt.Y("win_rate:Q", title="Win Rate", axis=alt.Axis(format=".0%")),
        size=alt.Size("pipeline_value_usd:Q", title="Pipeline Value", legend=None),
        color=alt.Color("acquirer_segment:N", title="Segment",
                        scale=alt.Scale(range=CATEGORY_RANGE)),
        tooltip=[
            "acquirer_segment:N",
            alt.Tooltip("deal_size_k:Q", title="Avg Deal Size ($K)", format="$,.0f"),
            alt.Tooltip("win_rate:Q", title="Win Rate", format=".1%"),
            alt.Tooltip("pipeline_value_usd:Q", title="Pipeline Value", format="$,.0f"),
        ],
    )
    .properties(height=300)
)
st.altair_chart(style(scatter_chart), use_container_width=True)
insight(
    "Bubble size = pipeline value. Top-right is the sweet spot (high value, high win "
    "rate); segments low and to the right are big deals that are hard to win — where "
    "enablement and deal support pay off most."
)
