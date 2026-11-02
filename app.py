"""Streamlit entrypoint for the ActuarialAI reserving MVP."""
import plotly.express as px
import streamlit as st

from actuarial_ai import chain_ladder, synthetic_triangle
from actuarial_ai.backtest import backtest_metrics, rolling_backtest
from actuarial_ai.data_io import load_triangle, triangle_csv
from actuarial_ai.explainability import factor_feature_importance
from actuarial_ai.governance import monitoring_report
from actuarial_ai.ml import holdout_last_diagonal, ml_reserving
from actuarial_ai.portfolio import portfolio_report, portfolio_scenarios
from actuarial_ai.portfolio_backtest import portfolio_backtest
from actuarial_ai.portfolio_governance import (
    governance_assessment,
    governance_audit_report,
)
from actuarial_ai.portfolio_io import load_portfolio_csv
from actuarial_ai.portfolio_risk import simulate_portfolio_risk
from actuarial_ai.quality import quality_csv, quality_report
from actuarial_ai.report_builder import ReportOptions, configurable_portfolio_pdf
from actuarial_ai.report_history import get_report, list_reports, save_report
from actuarial_ai.reporting import analysis_report, report_json
from actuarial_ai.risk_sensitivity import portfolio_risk_sensitivity
from actuarial_ai.scenarios import scenario_comparison, sensitivity_grid
from actuarial_ai.shap_explain import shap_factor_explanations
from actuarial_ai.uncertainty import bootstrap_reserves
from actuarial_ai.validation import validate_models, validation_report

st.set_page_config(page_title="ActuarialAI | Reserving", layout="wide")
st.title("ActuarialAI — Chain-Ladder Reserving")
st.caption("Educational demonstration with synthetic cumulative paid claims; not for production actuarial decisions.")
n = st.sidebar.slider("Origin periods", 4, 12, 8)
seed = st.sidebar.number_input("Random seed", min_value=0, value=42)
triangle = synthetic_triangle(n, int(seed))
uploaded = st.sidebar.file_uploader("Claims triangle (.csv or .xlsx)", type=["csv", "xlsx"])
source_name = "synthetic"
if uploaded is not None:
    try:
        triangle = load_triangle(uploaded.getvalue(), uploaded.name)
        source_name = uploaded.name
        n = len(triangle)
        st.sidebar.success(f"Validated {n} origin periods")
    except ValueError as exc:
        st.error(f"Invalid claims triangle: {exc}")
        st.stop()
st.sidebar.caption("Uploaded files are processed in the running application. Avoid uploading sensitive claims data to untrusted deployments.")
st.download_button("Download validated triangle (CSV)", triangle_csv(triangle),
                   file_name="claims_triangle.csv", mime="text/csv")
st.download_button("Download Chain-Ladder report (JSON)",
                   report_json(analysis_report(triangle, source=source_name)),
                   file_name="actuarial_report.json", mime="application/json")
quality = quality_report(triangle)
st.subheader("Data quality and anomaly diagnostics")
st.caption("Age-specific median/MAD screening; flagged pairs require actuarial review. Sparse ages are unassessable, not normal.")
q = quality["summary"]
col1, col2, col3 = st.columns(3)
col1.metric("Observed cells", q["observed_cells"])
col2.metric("Flagged development pairs", q["flagged_pairs"])
col3.metric("Unassessable pairs", q["unassessable_pairs"])
st.dataframe(quality["flags"], use_container_width=True)
with st.expander("All development-pair diagnostics"):
    st.dataframe(quality["diagnostics"], use_container_width=True)
st.download_button("Download quality diagnostics (CSV)", quality_csv(quality),
                   file_name="quality_diagnostics.csv", mime="text/csv")
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

if n >= 6:
    st.subheader("SHAP factor explanations (optional)")
    st.caption("In-sample contributions to predicted development factors, not causal effects or reserve-level explanations.")
    if st.checkbox("Compute SHAP explanations", value=False):
        try:
            shap_result = shap_factor_explanations(triangle)
            st.dataframe(shap_result["importance"], use_container_width=True)
            st.bar_chart(shap_result["importance"].set_index("feature")["mean_absolute_shap"])
            st.dataframe(shap_result["details"], use_container_width=True)
        except (ImportError, ValueError) as exc:
            st.warning(str(exc))

st.subheader("Scenario analysis and stress testing")
st.caption("Illustrative deterministic shocks applied only to future incremental payments; not a calibrated forecast.")
inflation_stress = st.slider("Annual future-payment inflation stress (%)", 0, 30, 5, step=1) / 100
factor_stress = st.slider("Future development increment stress (%)", 0, 30, 10, step=1) / 100
scenarios = scenario_comparison(triangle, inflation_stress, factor_stress)
st.dataframe(scenarios, use_container_width=True)
st.bar_chart(scenarios.set_index("scenario")["total_reserve"])
st.download_button("Download scenario comparison (CSV)",
                   scenarios.to_csv(index=False).encode("utf-8"),
                   file_name="reserve_scenarios.csv", mime="text/csv")
sensitivity = sensitivity_grid(
    triangle, (-inflation_stress, 0.0, inflation_stress),
    (-factor_stress, 0.0, factor_stress),
)
st.caption("Reserve sensitivity by combined future inflation and development shocks")
st.dataframe(sensitivity, use_container_width=True)
st.download_button("Download sensitivity grid (CSV)",
                   sensitivity.to_csv(index=False).encode("utf-8"),
                   file_name="reserve_sensitivity.csv", mime="text/csv")

st.subheader("Multi-segment portfolio analysis")
st.caption("Upload long-form CSV: segment, origin, development, cumulative_paid. Development labels must sort in age order (e.g. D01, D02).")
portfolio_upload = st.file_uploader("Portfolio CSV", type=["csv"], key="portfolio_csv")
if portfolio_upload is not None:
    try:
        segments = load_portfolio_csv(portfolio_upload.getvalue())
        portfolio = portfolio_report(segments, inflation_stress, factor_stress)
        totals = portfolio["totals"]
        pc1, pc2, pc3 = st.columns(3)
        pc1.metric("Portfolio baseline reserve", f"{totals['baseline_reserve']:,.0f}")
        pc2.metric("Portfolio stressed reserve", f"{totals['stressed_reserve']:,.0f}")
        pc3.metric("Portfolio reserve delta", f"{totals['reserve_delta']:,.0f}")
        st.dataframe(portfolio["segments"], use_container_width=True)
        st.bar_chart(portfolio["segments"].set_index("segment")[["baseline_reserve", "stressed_reserve"]])
        st.download_button("Download portfolio segment report (CSV)",
                           portfolio["segments"].to_csv(index=False).encode("utf-8"),
                           file_name="portfolio_segments.csv", mime="text/csv")
        st.subheader("Portfolio Monte Carlo risk (experimental)")
        st.caption("Illustrative correlated lognormal reserve shocks, not a calibrated predictive model.")
        if st.checkbox("Run portfolio Monte Carlo", value=False):
            simulations = st.slider("Portfolio Monte Carlo simulations", 500, 10000, 2000, 500)
            volatility = st.slider("Reserve volatility (%)", 0, 100, 20, 5) / 100
            correlation = st.slider("Cross-segment latent correlation", 0.0, 1.0, 0.25, 0.05)
            confidence = st.selectbox("Risk quantile", [0.90, 0.95, 0.99], index=1)
            risk = simulate_portfolio_risk(
                segments, simulations=simulations, volatility=volatility,
                correlation=correlation, confidence=confidence, seed=int(seed),
            )
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Simulated mean reserve", f"{risk['mean']:,.0f}")
            mc2.metric("Reserve VaR", f"{risk['var']:,.0f}")
            mc3.metric("Expected shortfall", f"{risk['expected_shortfall']:,.0f}")
            st.plotly_chart(
                px.histogram(x=risk["portfolio_samples"], nbins=50,
                             labels={"x": "Simulated portfolio reserve"}),
                use_container_width=True,
            )
            st.dataframe(risk["segment_summary"], use_container_width=True)
            simulation_table = risk["samples"].copy()
            simulation_table["portfolio_total"] = risk["portfolio_samples"]
            st.download_button(
                "Download Monte Carlo simulations (CSV)",
                simulation_table.to_csv(index=False).encode("utf-8"),
                file_name="portfolio_monte_carlo.csv", mime="text/csv",
            )
        if st.checkbox("Run portfolio risk sensitivity grid", value=False):
            grid = portfolio_risk_sensitivity(
                segments, simulations=2000, confidence=0.95, seed=int(seed),
            )
            st.caption("Assumption scenarios: volatility × latent correlation; not calibrated.")
            st.dataframe(grid, use_container_width=True)
            st.dataframe(
                grid.pivot(index="volatility", columns="correlation", values="var"),
                use_container_width=True,
            )
            st.download_button(
                "Download portfolio risk sensitivity (CSV)",
                grid.to_csv(index=False).encode("utf-8"),
                file_name="portfolio_risk_sensitivity.csv", mime="text/csv",
            )
        if st.checkbox("Run historical portfolio backtest", value=False):
            try:
                history = portfolio_backtest(segments)
                st.caption(history["limitations"])
                st.dataframe(history["metrics"], use_container_width=True)
                st.dataframe(history["portfolio"], use_container_width=True)
                with st.expander("Segment-level historical holdouts"):
                    st.dataframe(history["by_segment"], use_container_width=True)
                st.download_button(
                    "Download historical portfolio backtest (CSV)",
                    history["portfolio"].to_csv(index=False).encode("utf-8"),
                    file_name="portfolio_backtest.csv", mime="text/csv",
                )
            except ValueError as exc:
                st.info(f"Portfolio backtest unavailable: {exc}")
        if st.checkbox("Run portfolio model governance assessment", value=False):
            min_valuations = st.number_input("Minimum common valuations", min_value=1, value=3)
            max_mae_ratio = st.number_input(
                "Maximum ML/Chain-Ladder MAE ratio", min_value=0.01, value=1.10,
            )
            max_underprediction_rate = st.slider(
                "Maximum ML underprediction rate", 0.0, 1.0, 0.75, 0.05,
            )
            try:
                options = {
                    "min_valuations": int(min_valuations),
                    "max_mae_ratio": float(max_mae_ratio),
                    "max_underprediction_rate": float(max_underprediction_rate),
                }
                assessment = governance_assessment(segments, **options)
                st.metric("Diagnostic status (not model approval)", assessment["status"])
                st.dataframe(assessment["checks"], use_container_width=True)
                st.dataframe(assessment["metrics"], use_container_width=True)
                st.caption(assessment["limitations"])
                st.download_button(
                    "Download governance audit report (JSON)",
                    report_json(governance_audit_report(
                        segments, source=portfolio_upload.name, **options,
                    )),
                    file_name="portfolio_governance_audit.json",
                    mime="application/json",
                )
            except ValueError as exc:
                st.info(f"Governance assessment unavailable: {exc}")
        if st.checkbox("Generate configurable portfolio PDF report", value=False):
            with st.expander("Report configuration", expanded=True):
                show_segments = st.checkbox("Include segment reserves", value=True)
                show_charts = st.checkbox("Include reserve chart", value=True)
                show_risk = st.checkbox("Include Monte Carlo risk", value=True)
                show_governance = st.checkbox("Include governance", value=True)
                report_confidence = st.selectbox(
                    "Report risk confidence", [0.90, 0.95, 0.99], index=1,
                )
                report_simulations = st.number_input(
                    "Report simulations", min_value=100, max_value=20000,
                    value=2000, step=100,
                )
            try:
                settings = ReportOptions(
                    include_segments=show_segments,
                    include_charts=show_charts,
                    include_risk=show_risk,
                    include_governance=show_governance,
                    confidence=float(report_confidence),
                    simulations=int(report_simulations),
                    seed=int(seed),
                )
                pdf, version = configurable_portfolio_pdf(
                    segments, source=portfolio_upload.name, options=settings,
                )
                st.caption(f"Report version (SHA-256): {version}")
                st.download_button(
                    "Download configured portfolio report (PDF)", pdf,
                    file_name=f"portfolio_report_{version[:12]}.pdf",
                    mime="application/pdf",
                )
                if st.button("Save report snapshot to local history"):
                    try:
                        audit = None
                        if settings.include_governance:
                            try:
                                audit = governance_assessment(segments)
                            except ValueError:
                                pass
                        record_id = save_report(
                            "data/actuarialai_reports.sqlite3",
                            version=version, source=portfolio_upload.name,
                            portfolio_csv=portfolio_upload.getvalue(), pdf=pdf,
                            options=settings,
                            summary={
                                "segments": len(segments),
                                "baseline_reserve": float(
                                    portfolio["totals"]["baseline_reserve"]
                                ),
                                "latest_paid": float(portfolio["totals"]["latest_paid"]),
                            },
                            governance=audit,
                        )
                        st.success(f"Saved report #{record_id}")
                    except (OSError, ValueError) as exc:
                        st.error(f"Could not save report: {exc}")
            except ValueError as exc:
                st.warning(f"PDF report unavailable: {exc}")
        portfolio_cases = portfolio_scenarios(segments, inflation_stress, factor_stress)
        st.dataframe(portfolio_cases, use_container_width=True)
        st.download_button("Download portfolio scenarios (CSV)",
                           portfolio_cases.to_csv(index=False).encode("utf-8"),
                           file_name="portfolio_scenarios.csv", mime="text/csv")
    except (TypeError, ValueError) as exc:
        st.error(f"Invalid portfolio data: {exc}")

st.subheader("Saved portfolio report history (local SQLite)")
st.caption(
    "Reports are saved only when requested. The database is local to this "
    "Streamlit server; it has no authentication or encryption."
)
try:
    saved_reports = list_reports("data/actuarialai_reports.sqlite3")
    if saved_reports:
        st.dataframe(
            [
                {
                    "id": item["id"],
                    "created_utc": item["created_utc"],
                    "source": item["source"],
                    "version": item["version"][:12],
                    "baseline_reserve": item["summary"].get("baseline_reserve"),
                    "governance_status": (
                        item["governance"].get("status")
                        if item["governance"] else "NOT ASSESSED"
                    ),
                }
                for item in saved_reports
            ],
            use_container_width=True,
        )
        selected_id = st.selectbox(
            "Select saved report", [item["id"] for item in saved_reports],
            format_func=lambda value: f"Report #{value}",
        )
        selected = get_report("data/actuarialai_reports.sqlite3", selected_id)
        if selected is not None:
            st.json({
                "created_utc": selected["created_utc"],
                "version": selected["version"],
                "options": selected["options"],
                "summary": selected["summary"],
                "governance": selected["governance"],
            })
            st.download_button(
                "Download saved PDF", selected["pdf"],
                file_name=f"portfolio_report_{selected['version'][:12]}.pdf",
                mime="application/pdf",
            )
            st.download_button(
                "Download saved source CSV", selected["portfolio_csv"],
                file_name=f"portfolio_source_{selected_id}.csv",
                mime="text/csv",
            )
        if len(saved_reports) > 1:
            first, second = st.columns(2)
            ids = [item["id"] for item in saved_reports]
            left_id = first.selectbox("Compare report A", ids, index=1)
            right_id = second.selectbox("Compare report B", ids, index=0)
            left = next(item for item in saved_reports if item["id"] == left_id)
            right = next(item for item in saved_reports if item["id"] == right_id)
            a = left["summary"].get("baseline_reserve", 0)
            b = right["summary"].get("baseline_reserve", 0)
            st.metric("Baseline reserve change (B - A)", f"{b - a:,.2f}")
    else:
        st.info("No saved reports yet.")
except (OSError, ValueError) as exc:
    st.warning(f"Report history unavailable: {exc}")

st.subheader("Model validation and governance")
st.caption("Rolling one-step cumulative-paid holdouts; metrics do not validate ultimate reserves.")
if st.checkbox("Run model validation", value=False):
    try:
        validation = validate_models(triangle)
        st.dataframe(validation["metrics"], use_container_width=True)
        st.dataframe(validation["by_valuation"], use_container_width=True)
        st.metric("ML monitoring alerts", validation["alert_count"])
        st.caption(f"Lowest observed holdout MAE: {validation['preferred_by_mae']}")
        st.download_button(
            "Download model validation report (JSON)",
            report_json(validation_report(triangle, source=source_name)),
            file_name="model_validation.json", mime="application/json",
        )
    except ValueError as exc:
        st.warning(f"Model validation unavailable: {exc}")
