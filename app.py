"""Streamlit entrypoint for the ActuarialAI reserving MVP."""
import plotly.express as px
import streamlit as st

from actuarial_ai import chain_ladder, synthetic_triangle
from actuarial_ai.backtest import backtest_metrics, rolling_backtest
from actuarial_ai.explainability import factor_feature_importance
from actuarial_ai.governance import monitoring_report
from actuarial_ai.ml import holdout_last_diagonal, ml_reserving
from actuarial_ai.uncertainty import bootstrap_reserves

st.set_page_config(page_title="ActuarialAI | Reserving", layout="wide")
st.title("ActuarialAI — Chain-Ladder Reserving")
st.caption("Educational demonstration with synthetic cumulative paid claims; not for production actuarial decisions.")
n = st.sidebar.slider("Origin periods", 4, 12, 8)
seed = st.sidebar.number_input("Random seed", min_value=0, value=42)
triangle = synthetic_triangle(n, int(seed))
result = chain_ladder(triangle)
st.metric("Estimated outstanding reserve", f"{result['total_reserve']:,.0f} synthetic units")
st.subheader("Observed cumulative claims triangle")
st.dataframe(triangle, use_container_width=True)
st.subheader("Development factors")
st.dataframe(result["factors"].to_frame().T, use_container_width=True)
st.subheader("Origin-period reserves")
st.dataframe(result["summary"], use_container_width=True)
fig = px.bar(result["summary"].reset_index(), x="index", y="reserve", labels={"index": "Origin period", "reserve": "Reserve (synthetic units)"})
st.plotly_chart(fig, use_container_width=True)
st.subheader("Completed claims triangle")
st.dataframe(result["completed"], use_container_width=True)

st.subheader("Experimental ML benchmark")
st.caption("Random forest predicts age-to-age factors; sparse ages fall back to classical factors. Not production-calibrated.")
if n >= 6:
    ml = ml_reserving(triangle)
    comparison = result["summary"][["reserve"]].rename(columns={"reserve": "Chain-Ladder"})
    comparison["Random Forest"] = ml["summary"]["reserve"]
    st.dataframe(comparison, use_container_width=True)
    st.bar_chart(comparison)
    try:
        holdout = holdout_last_diagonal(triangle)
        st.metric("ML one-step diagonal holdout MAE", f"{holdout['mae']:,.0f} synthetic units")
        st.dataframe(holdout["predictions"], use_container_width=True)
    except ValueError as exc:
        st.info(str(exc))
else:
    st.info("Select at least six origin periods to run the experimental ML benchmark.")

st.subheader("Rolling calendar-time backtest")
st.caption("Both models are evaluated on the same next-calendar-period paid observations; training uses earlier calendar diagonals only.")
predictions = rolling_backtest(triangle)
if predictions.empty:
    st.info("Insufficient historical development pairs for rolling backtest.")
else:
    st.dataframe(backtest_metrics(predictions), use_container_width=True)
    st.dataframe(predictions, use_container_width=True)
    st.subheader("Model governance monitoring")
    st.caption("Out-of-time MAE per valuation; alerts are illustrative and require human review.")
    monitoring = monitoring_report(predictions)
    st.metric("ML underperformance alerts", monitoring["alert_count"])
    st.dataframe(monitoring["by_valuation"], use_container_width=True)

st.subheader("Bootstrap reserve sensitivity")
st.caption("Educational resampling of development factors; not a calibrated reserve confidence interval.")
simulation_count = st.slider("Bootstrap simulations", 100, 1000, 300, step=100)
bootstrap = bootstrap_reserves(triangle, simulations=simulation_count, seed=int(seed))
st.write(f"Illustrative 90% sample quantile range: {bootstrap['lower']:,.0f} to {bootstrap['upper']:,.0f} synthetic units")
st.plotly_chart(px.histogram(x=bootstrap["samples"], nbins=35,
    labels={"x": "Simulated total reserve (synthetic units)"}), use_container_width=True)
if n >= 6:
    st.subheader("Experimental ML feature importance")
    st.caption("In-sample permutation importance; not causal and not validated out of sample.")
    importance = factor_feature_importance(triangle)
    st.dataframe(importance, use_container_width=True)
    st.bar_chart(importance.set_index("feature")["importance_mean"])
