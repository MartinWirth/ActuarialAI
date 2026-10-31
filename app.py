"""Streamlit entrypoint for the ActuarialAI reserving MVP."""
import streamlit as st
import plotly.express as px
from actuarial_ai import chain_ladder, synthetic_triangle
from actuarial_ai.ml import ml_reserving, holdout_last_diagonal

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
