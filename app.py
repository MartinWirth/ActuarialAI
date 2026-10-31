"""Streamlit entrypoint for the ActuarialAI reserving MVP."""
import streamlit as st
import plotly.express as px
from actuarial_ai import chain_ladder, synthetic_triangle

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
