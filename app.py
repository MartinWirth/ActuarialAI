"""Streamlit entrypoint for the ActuarialAI reserving MVP."""
import pandas as pd
import plotly.express as px
import streamlit as st

from actuarial_ai import chain_ladder, synthetic_triangle
from actuarial_ai.approval_workflow import (
    audit_events,
    audit_export,
    authenticated_transition,
    report_status,
    verify_audit_chain,
)
from actuarial_ai.auth import (
    change_password,
    create_user,
    has_users,
    identity,
    list_users,
    login,
    logout,
    require_permission,
    security_events,
    set_user_active,
)
from actuarial_ai.backtest import backtest_metrics, rolling_backtest
from actuarial_ai.data_io import load_triangle, triangle_csv
from actuarial_ai.explainability import factor_feature_importance
from actuarial_ai.governance import monitoring_report
from actuarial_ai.mack import mack_chain_ladder
from actuarial_ai.mack_matrix import aggregate_mack_matrix, validate_correlation_matrix
from actuarial_ai.mack_matrix_sensitivity import mack_matrix_sensitivity
from actuarial_ai.mack_sensitivity import mack_correlation_sensitivity
from actuarial_ai.ml import holdout_last_diagonal, ml_reserving
from actuarial_ai.portfolio import portfolio_report, portfolio_scenarios
from actuarial_ai.portfolio_backtest import portfolio_backtest
from actuarial_ai.portfolio_governance import (
    governance_assessment,
    governance_audit_report,
)
from actuarial_ai.portfolio_io import load_portfolio_csv
from actuarial_ai.portfolio_mack import aggregate_mack
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
DB_PATH = "data/actuarialai_reports.sqlite3"
if not has_users(DB_PATH):
    st.warning(
        "Initial local setup: create the first administrator account. "
        "Use a strong unique password and run only on a trusted machine."
    )
    with st.form("bootstrap_admin"):
        initial_username = st.text_input("Administrator username")
        initial_password = st.text_input("Administrator password", type="password")
        bootstrap = st.form_submit_button("Create administrator")
    if bootstrap:
        try:
            create_user(DB_PATH, initial_username, initial_password, "ADMIN")
            st.success("Administrator created. Sign in below.")
            st.rerun()
        except (ValueError, PermissionError) as exc:
            st.error(str(exc))
    st.stop()

session_token = st.session_state.get("auth_token")
current_user = identity(DB_PATH, session_token)
if current_user is None:
    st.session_state.pop("auth_token", None)
    with st.form("sign_in"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        sign_in = st.form_submit_button("Sign in")
    if sign_in:
        try:
            st.session_state["auth_token"] = login(DB_PATH, username, password)
            st.rerun()
        except PermissionError:
            st.error("Invalid credentials")
    st.stop()

st.sidebar.caption(
    f"Signed in: {current_user['username']} ({current_user['role']})"
)
if st.sidebar.button("Sign out"):
    logout(DB_PATH, session_token)
    st.session_state.pop("auth_token", None)
    st.rerun()

with st.sidebar.expander("Change password"):
    with st.form("password_change"):
        old_pw = st.text_input("Current password", type="password")
        new_pw = st.text_input("New password (12+ characters)", type="password")
        update_pw = st.form_submit_button("Change password")
    if update_pw:
        try:
            change_password(DB_PATH, session_token, old_pw, new_pw)
            st.session_state.pop("auth_token", None)
            st.success("Password changed; all sessions revoked. Sign in again.")
            st.rerun()
        except (ValueError, PermissionError) as exc:
            st.error(str(exc))

if current_user["role"] == "ADMIN":
    with st.sidebar.expander("User administration"):
        with st.form("new_user"):
            new_username = st.text_input("New username")
            new_password = st.text_input("New password", type="password")
            new_role = st.selectbox(
                "Role", ["ACTUARY", "REVIEWER", "AUDITOR", "ADMIN"],
            )
            create_account = st.form_submit_button("Create account")
        if create_account:
            try:
                create_user(
                    DB_PATH, new_username, new_password, new_role,
                    admin_token=session_token,
                )
                st.success("Account created")
            except (ValueError, PermissionError) as exc:
                st.error(str(exc))
        accounts = list_users(DB_PATH, session_token)
        st.dataframe(accounts)
        with st.form("account_state"):
            account_name = st.selectbox(
                "Account", [account["username"] for account in accounts],
            )
            enabled = st.checkbox("Account enabled", value=True)
            apply_state = st.form_submit_button("Apply account status")
        if apply_state:
            try:
                set_user_active(DB_PATH, session_token, account_name, enabled)
                st.success("Account status updated")
                st.rerun()
            except (ValueError, PermissionError) as exc:
                st.error(str(exc))
        st.caption("Recent security events (no passwords or session tokens)")
        st.dataframe(security_events(DB_PATH, session_token, limit=50))


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
st.subheader("Mack Chain-Ladder prediction uncertainty")
mack_confidence = st.select_slider(
    "Illustrative normal interval confidence",
    options=[0.80, 0.90, 0.95, 0.99],
    value=0.95,
)
try:
    mack = mack_chain_ladder(triangle, confidence=mack_confidence)
    st.metric("Mack aggregate prediction standard error", f"{mack['total_se']:,.0f}")
    st.write(
        f"Approximate {mack_confidence:.0%} reserve interval: "
        f"{mack['total_lower']:,.0f} – {mack['total_upper']:,.0f}"
    )
    st.dataframe(mack["summary"], use_container_width=True)
    with st.expander("Mack variance estimates and assumptions"):
        st.dataframe(mack["sigma2"].to_frame(), use_container_width=True)
        st.caption(mack["assumptions"])
    st.caption(
        "Mack MSEP includes process and parameter risk. Normal intervals are "
        "illustrative, not calibrated predictive coverage; zero is a floor."
    )
except ValueError as exc:
    st.warning(f"Mack uncertainty unavailable: {exc}")

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
        st.subheader("Portfolio Mack risk aggregation (assumption-driven)")
        st.caption(
            "Common pairwise correlation is assumed, not estimated. "
            "Normal intervals are illustrative, not calibrated."
        )
        mack_correlation = st.slider(
            "Assumed Mack cross-segment correlation", 0.0, 1.0, 0.0, 0.05,
        )
        use_mack_matrix = st.checkbox(
            "Use custom pairwise Mack correlation matrix", value=False,
        )
        custom_mack_matrix = None
        if use_mack_matrix:
            names = sorted(segments)
            default_matrix = pd.DataFrame(
                [[1.0 if a == b else float(mack_correlation)
                  for b in names] for a in names],
                index=names, columns=names,
            )
            edited_matrix = st.data_editor(
                default_matrix, key="mack_pairwise_matrix",
                use_container_width=True,
            )
            try:
                checked = validate_correlation_matrix(edited_matrix, names)
                custom_mack_matrix = pd.DataFrame(
                    checked, index=names, columns=names,
                )
                st.success("Correlation matrix is positive semidefinite.")
            except ValueError as exc:
                st.warning(f"Invalid correlation matrix: {exc}")
        if st.checkbox("Calculate aggregate Mack uncertainty", value=False):
            try:
                if use_mack_matrix:
                    if custom_mack_matrix is None:
                        raise ValueError("Correct the correlation matrix first")
                    aggregated = aggregate_mack_matrix(segments, custom_mack_matrix)
                else:
                    aggregated = aggregate_mack(
                        segments, correlation=mack_correlation,
                    )
                ma, mb, mc = st.columns(3)
                ma.metric("Aggregated Mack S.E.", f"{aggregated['total_se']:,.0f}")
                mb.metric("Independent Mack S.E.", f"{aggregated['independent_se']:,.0f}")
                mc.metric(
                    "Diversification vs standalone S.E.",
                    f"{aggregated['diversification_benefit']:,.0f}",
                )
                st.write(
                    f"95% approximate interval: {aggregated['lower']:,.0f} "
                    f"to {aggregated['upper']:,.0f}"
                )
                st.dataframe(aggregated["segments"], use_container_width=True)
            except ValueError as exc:
                st.warning(f"Portfolio Mack unavailable: {exc}")
        if st.checkbox("Run Mack correlation sensitivity", value=False):
            try:
                sensitivity = mack_correlation_sensitivity(segments)
                st.dataframe(sensitivity, use_container_width=True)
                st.line_chart(
                    sensitivity.set_index("correlation")[
                        ["total_se", "diversification_benefit"]
                    ],
                )
                st.download_button(
                    "Download Mack correlation sensitivity (CSV)",
                    sensitivity.to_csv(index=False).encode("utf-8"),
                    file_name="mack_correlation_sensitivity.csv",
                    mime="text/csv",
                )
            except ValueError as exc:
                st.warning(f"Mack sensitivity unavailable: {exc}")
        show_pairwise_sensitivity = st.checkbox(
            "Run pairwise Mack matrix sensitivity", value=False,
            disabled=not use_mack_matrix,
        )
        pairwise_shock = st.slider(
            "Pairwise correlation shock step", 0.05, 0.40, 0.10, 0.05,
            disabled=not show_pairwise_sensitivity,
        )
        if show_pairwise_sensitivity:
            if custom_mack_matrix is None:
                st.warning("Correct the correlation matrix before running sensitivity.")
            else:
                try:
                    scenarios = mack_matrix_sensitivity(
                        segments, custom_mack_matrix,
                        shocks=(-2 * pairwise_shock, -pairwise_shock, 0.0,
                                pairwise_shock, 2 * pairwise_shock),
                    )
                    st.dataframe(scenarios, use_container_width=True)
                    valid_scenarios = scenarios[scenarios["valid_psd"]]
                    if not valid_scenarios.empty:
                        heatmap_data = valid_scenarios.pivot(
                            index=["segment_a", "segment_b"],
                            columns="shock", values="delta_se",
                        )
                        heatmap_data.index = [
                            f"{a} / {b}" for a, b in heatmap_data.index
                        ]
                        fig = px.imshow(
                            heatmap_data, aspect="auto",
                            labels={"x": "Pairwise shock", "y": "Segment pair",
                                    "color": "Change in Mack S.E."},
                            title="Mack portfolio risk sensitivity",
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    st.caption(
                        "Only one symmetric pair changes per scenario. "
                        "Non-PSD scenarios are excluded from the heatmap and "
                        "have no reported risk estimate."
                    )
                    st.download_button(
                        "Download pairwise Mack sensitivity (CSV)",
                        scenarios.to_csv(index=False).encode("utf-8"),
                        file_name="mack_pairwise_sensitivity.csv",
                        mime="text/csv",
                    )
                except ValueError as exc:
                    st.warning(f"Pairwise Mack sensitivity unavailable: {exc}")
        if st.checkbox("Generate configurable portfolio PDF report", value=False):
            with st.expander("Report configuration", expanded=True):
                show_segments = st.checkbox("Include segment reserves", value=True)
                show_charts = st.checkbox("Include reserve chart", value=True)
                show_risk = st.checkbox("Include Monte Carlo risk", value=True)
                show_governance = st.checkbox("Include governance", value=True)
                show_mack = st.checkbox("Include Mack uncertainty by segment", value=True)
                show_mack_sensitivity = st.checkbox(
                    "Include Mack correlation sensitivity", value=True,
                )
                show_pairwise_pdf = st.checkbox(
                    "Include pairwise Mack matrix sensitivity", value=False,
                    disabled=not (show_mack and use_mack_matrix),
                )
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
                    include_mack=show_mack,
                    include_mack_sensitivity=show_mack and show_mack_sensitivity,
                    include_mack_matrix_sensitivity=(
                        show_mack and use_mack_matrix and show_pairwise_pdf
                    ),
                    mack_matrix_shock=float(pairwise_shock),
                    mack_correlation=float(mack_correlation),
                    mack_matrix=(
                        tuple(tuple(float(v) for v in row)
                              for row in custom_mack_matrix.to_numpy())
                        if show_mack and use_mack_matrix and custom_mack_matrix is not None
                        else None
                    ),
                    confidence=float(report_confidence),
                    simulations=int(report_simulations),
                    seed=int(seed),
                )
                if show_mack and use_mack_matrix and custom_mack_matrix is None:
                    raise ValueError("Correct the correlation matrix before PDF export")
                pdf, version = configurable_portfolio_pdf(
                    segments, source=portfolio_upload.name, options=settings,
                )
                st.caption(f"Report version (SHA-256): {version}")
                st.download_button(
                    "Download configured portfolio report (PDF)", pdf,
                    file_name=f"portfolio_report_{version[:12]}.pdf",
                    mime="application/pdf",
                )
                if st.button(
                    "Save report snapshot to local history",
                    disabled=current_user["role"] not in {"ADMIN", "ACTUARY"},
                ):
                    try:
                        audit = None
                        if settings.include_governance:
                            try:
                                audit = governance_assessment(segments)
                            except ValueError:
                                pass
                        require_permission(DB_PATH, session_token, "save_reports")
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
    "Streamlit server; login is required but database encryption is not enabled."
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
            st.subheader("Report governance workflow (local demonstration)")
            try:
                current_status = report_status(
                    "data/actuarialai_reports.sqlite3", selected_id,
                )
                st.metric("Approval workflow status", current_status)
                history_events = audit_events(
                    "data/actuarialai_reports.sqlite3", selected_id,
                )
                st.caption(
                    "Decisions use the signed-in identity. Local session and "
                    "hash chain are not protection against server administrators "
                    "or direct database modification."
                )
                if history_events:
                    st.dataframe(history_events, use_container_width=True)
                st.caption(
                    "Audit chain integrity: "
                    + ("valid" if verify_audit_chain(history_events) else "INVALID")
                )
                st.download_button(
                    "Download approval audit log (JSON)",
                    audit_export("data/actuarialai_reports.sqlite3", selected_id),
                    file_name=f"approval_audit_{selected_id}.json",
                    mime="application/json",
                )
                allowed = {
                    "DRAFT": ["IN_REVIEW"],
                    "IN_REVIEW": ["APPROVED", "REJECTED"],
                    "REJECTED": ["IN_REVIEW"],
                    "APPROVED": [],
                }[current_status]
                if allowed:
                    with st.form(f"approval_transition_{selected_id}"):
                        decision = st.selectbox("Next workflow status", allowed)
                        justification = st.text_area("Reason / review notes")
                        submit_decision = st.form_submit_button(
                            "Record decision",
                            disabled=(
                                current_user["role"] not in {"ADMIN", "ACTUARY"}
                                if current_status in {"DRAFT", "REJECTED"}
                                else current_user["role"] != "REVIEWER"
                            ),
                        )
                    if submit_decision:
                        try:
                            authenticated_transition(
                                DB_PATH, selected_id, session_token,
                                decision, justification,
                            )
                            st.success("Decision recorded in append-only audit log.")
                            st.rerun()
                        except (OSError, ValueError, PermissionError) as exc:
                            st.error(f"Decision not recorded: {exc}")
            except (OSError, ValueError) as exc:
                st.error(f"Governance workflow unavailable: {exc}")
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
