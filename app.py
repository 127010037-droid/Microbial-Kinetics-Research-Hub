
import streamlit as st
from io import BytesIO
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from analysis import fit_growth_models

from models import (
    logistic_model,
    gompertz_model,
    baranyi_model
)

from database import (
    create_tables,
    save_experiment,
    save_growth_data,
    get_experiments,
    get_growth_data,
    get_model_results,
    save_model_results
)


def create_excel_workbook(sheets):
    """Create an Excel workbook in memory from DataFrames."""
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, dataframe in sheets.items():
            if dataframe is None:
                dataframe = pd.DataFrame()

            dataframe.to_excel(
                writer,
                sheet_name=str(sheet_name)[:31],
                index=False
            )

    output.seek(0)
    return output.getvalue()


# =====================================================
# PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="Microbial Kinetics Research Hub",
    page_icon="🧫",
    layout="wide"
)

st.title("🧫 Microbial Kinetics Research Hub")

st.markdown("""
### Integrated Microbial Growth Analysis and Comparative Database

Upload experimental data, fit mathematical growth models,
compare their statistical performance and store your results.
""")

st.divider()


# =====================================================
# DATABASE CONNECTION
# =====================================================

try:
    create_tables()
    database_connected = True

except Exception as error:
    database_connected = False
    st.error(f"Database connection failed: {error}")


# =====================================================
# SIDEBAR NAVIGATION
# =====================================================

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Select a section",
    [
        "Growth Analysis",
        "Experiment History",
        "Experiment Comparison"
    ]
)


# =====================================================
# PAGE 1: GROWTH ANALYSIS
# =====================================================

if page == "Growth Analysis":

    st.header("1. Upload Experimental Data")

    uploaded_file = st.file_uploader(
        "Upload your CSV file",
        type=["csv"],
        key="growth_csv"
    )

    if uploaded_file is not None:

        try:
            data = pd.read_csv(uploaded_file)

            if "Time" not in data.columns or "OD" not in data.columns:
                st.error("CSV must contain Time and OD columns.")

            else:
                data = data[["Time", "OD"]].copy()

                data["Time"] = pd.to_numeric(
                    data["Time"], errors="coerce"
                )

                data["OD"] = pd.to_numeric(
                    data["OD"], errors="coerce"
                )

                data = data.dropna().sort_values("Time")

                if len(data) < 5:
                    st.error(
                        "At least 5 valid data points are required."
                    )

                else:
                    st.success("Data uploaded successfully!")

                    st.subheader("Experimental Data")

                    st.dataframe(
                        data,
                        use_container_width=True
                    )

                    # EXPERIMENTAL GROWTH CURVE

                    st.header("2. Experimental Growth Curve")

                    figure = go.Figure()

                    figure.add_trace(go.Scatter(
                        x=data["Time"],
                        y=data["OD"],
                        mode="markers+lines",
                        name="Experimental data"
                    ))

                    figure.update_layout(
                        title="Microbial Growth Curve",
                        xaxis_title="Time",
                        yaxis_title="Optical Density (OD)"
                    )

                    st.plotly_chart(
                        figure,
                        use_container_width=True
                    )

                    # EXPERIMENT INFORMATION

                    st.header("3. Experiment Information")

                    organism = st.text_input(
                        "Microorganism name",
                        placeholder="Example: Escherichia coli"
                    )

                    strain = st.text_input(
                        "Strain name",
                        placeholder="Enter strain name"
                    )

                    col1, col2 = st.columns(2)

                    with col1:
                        temperature = st.number_input(
                            "Temperature (°C)",
                            value=37.0
                        )

                    with col2:
                        ph = st.number_input(
                            "Initial pH",
                            min_value=0.0,
                            max_value=14.0,
                            value=7.0
                        )

                    # GROWTH MODEL FITTING

                    st.header("4. Growth Model Fitting")

                    if st.button(
                        "Fit All Growth Models",
                        type="primary"
                    ):

                        try:
                            results = fit_growth_models(
                                data["Time"].to_numpy(),
                                data["OD"].to_numpy()
                            )

                            st.session_state["fit_results"] = results
                            st.session_state["growth_data"] = data.copy()

                            st.success(
                                "Growth model fitting completed!"
                            )

                        except Exception as error:
                            st.error(
                                f"Model fitting failed: {error}"
                            )

                            st.session_state.pop(
                                "fit_results", None
                            )

                            st.session_state.pop(
                                "growth_data", None
                            )

                    # DISPLAY MODEL RESULTS

                    if (
                        "fit_results" in st.session_state
                        and "growth_data" in st.session_state
                    ):

                        results = st.session_state["fit_results"]
                        growth_data = st.session_state["growth_data"]

                        model_functions = {
                            "Logistic": logistic_model,
                            "Gompertz": gompertz_model,
                            "Baranyi": baranyi_model
                        }

                        successful = {
                            name: result
                            for name, result in results.items()
                            if result.get("success", False)
                        }

                        if successful:

                            # FITTED GROWTH CURVES

                            st.subheader("5. Fitted Growth Curves")

                            smooth_time = np.linspace(
                                growth_data["Time"].min(),
                                growth_data["Time"].max(),
                                250
                            )

                            fitted_figure = go.Figure()

                            fitted_figure.add_trace(go.Scatter(
                                x=growth_data["Time"],
                                y=growth_data["OD"],
                                mode="markers",
                                name="Experimental data"
                            ))

                            for name, result in successful.items():

                                parameters = list(
                                    result["parameters"].values()
                                )

                                fitted_values = model_functions[name](
                                    smooth_time,
                                    *parameters
                                )

                                fitted_figure.add_trace(go.Scatter(
                                    x=smooth_time,
                                    y=fitted_values,
                                    mode="lines",
                                    name=f"{name} model"
                                ))

                            fitted_figure.update_layout(
                                title="Experimental Data vs Fitted Models",
                                xaxis_title="Time",
                                yaxis_title="Optical Density (OD)"
                            )

                            st.plotly_chart(
                                fitted_figure,
                                use_container_width=True
                            )

                            # MODEL COMPARISON

                            st.subheader("6. Model Comparison")

                            comparison = []

                            for name, result in successful.items():
                                row = {"Model": name}
                                row.update(result["metrics"])
                                comparison.append(row)

                            comparison_df = pd.DataFrame(comparison)

                            st.dataframe(
                                comparison_df.round(5),
                                use_container_width=True
                            )

                            # RESIDUAL ANALYSIS

                            st.subheader("7. Residual Analysis")

                            residual_figure = go.Figure()

                            for name, result in successful.items():
                                residual_figure.add_trace(go.Scatter(
                                    x=growth_data["Time"],
                                    y=result["residuals"],
                                    mode="markers+lines",
                                    name=name
                                ))

                            residual_figure.add_hline(
                                y=0,
                                line_dash="dash"
                            )

                            residual_figure.update_layout(
                                title="Residual Plot",
                                xaxis_title="Time",
                                yaxis_title="Observed OD - Predicted OD"
                            )

                            st.plotly_chart(
                                residual_figure,
                                use_container_width=True
                            )

                            # PARAMETER ESTIMATION

                            st.subheader("8. Estimated Growth Parameters")

                            for name, result in successful.items():

                                st.markdown(f"**{name} Model**")

                                parameter_names = list(
                                    result["parameters"].keys()
                                )

                                parameter_values = list(
                                    result["parameters"].values()
                                )

                                ci = result.get("confidence_intervals")

                                if ci is not None:
                                    parameter_df = pd.DataFrame({
                                        "Parameter": parameter_names,
                                        "Estimated Value": parameter_values,
                                        "Standard Error": ci["standard_errors"],
                                        "95% CI Lower": ci["lower"],
                                        "95% CI Upper": ci["upper"]
                                    })

                                else:
                                    parameter_df = pd.DataFrame({
                                        "Parameter": parameter_names,
                                        "Estimated Value": parameter_values
                                    })

                                    st.info(
                                        "Confidence intervals unavailable."
                                    )

                                st.dataframe(
                                    parameter_df.round(5),
                                    use_container_width=True
                                )

                            st.caption(
                                "Confidence intervals are approximate and "
                                "depend on model fitting assumptions."
                            )

                        else:
                            st.error(
                                "No growth model could be fitted."
                            )

                        # SAVE EXPERIMENT

                        st.divider()

                        st.header("9. Save Experiment to MySQL")

                        if st.button("Save Experiment and Model Results"):

                            if not database_connected:
                                st.error("Database is not connected.")

                            elif not organism.strip():
                                st.error(
                                    "Please enter the microorganism name."
                                )

                            elif not successful:
                                st.error(
                                    "No successful model results available."
                                )

                            else:
                                try:
                                    experiment_id = save_experiment(
                                        organism.strip(),
                                        strain.strip() or None,
                                        temperature,
                                        ph
                                    )

                                    save_growth_data(
                                        experiment_id,
                                        growth_data
                                    )

                                    save_model_results(
                                        experiment_id,
                                        results
                                    )

                                    st.success(
                                        "Experiment, growth data and model "
                                        f"results saved successfully! "
                                        f"Experiment ID: {experiment_id}"
                                    )

                                except Exception as error:
                                    st.error(
                                        f"Database saving failed: {error}"
                                    )

        except Exception as error:
            st.error(
                f"Could not read the CSV file: {error}"
            )

    else:
        st.info(
            "Upload a CSV file containing Time and OD columns to begin."
        )


# =====================================================
# PAGE 2: EXPERIMENT HISTORY
# =====================================================

elif page == "Experiment History":

    st.header("📚 Experiment History Dashboard")

    st.write(
        "View and retrieve previously saved microbial growth experiments."
    )

    try:
        experiments = get_experiments()

        if experiments.empty:
            st.info("No saved experiments found.")

        else:
            search_name = st.text_input(
                "Search by microorganism name"
            )

            filtered = experiments[
                experiments["organism_name"].str.contains(
                    search_name,
                    case=False,
                    na=False
                )
            ]

            st.subheader("Saved Experiments")

            st.metric(
                "Total Experiments",
                len(experiments)
            )

            st.dataframe(
                filtered,
                use_container_width=True,
                hide_index=True
            )

            if not filtered.empty:

                st.divider()

                st.subheader("Retrieve Experiment")

                selected_id = st.selectbox(
                    "Select Experiment ID",
                    filtered["experiment_id"].tolist()
                )

                selected_experiment = filtered[
                    filtered["experiment_id"] == selected_id
                ].iloc[0]

                st.write("### Experiment Details")

                col1, col2, col3 = st.columns(3)

                col1.metric(
                    "Microorganism",
                    selected_experiment["organism_name"]
                )

                col2.metric(
                    "Temperature",
                    f"{selected_experiment['temperature']} °C"
                )

                col3.metric(
                    "Initial pH",
                    selected_experiment["ph"]
                )

                st.write(
                    "**Strain:**",
                    selected_experiment["strain_name"] or "Not specified"
                )

                # RETRIEVE ORIGINAL DATA

                growth_data = get_growth_data(selected_id)

                st.subheader("Retrieved Growth Data")

                st.dataframe(
                    growth_data,
                    use_container_width=True,
                    hide_index=True
                )

                # PLOT RETRIEVED DATA

                history_figure = go.Figure()

                history_figure.add_trace(go.Scatter(
                    x=growth_data["Time"],
                    y=growth_data["OD"],
                    mode="markers+lines",
                    name="Saved experimental data"
                ))

                history_figure.update_layout(
                    title=f"Growth Curve - Experiment {selected_id}",
                    xaxis_title="Time",
                    yaxis_title="Optical Density (OD)"
                )

                st.plotly_chart(
                    history_figure,
                    use_container_width=True
                )

                # DOWNLOAD DATA AS CSV

                csv_data = growth_data.to_csv(index=False)

                st.download_button(
                    "Download Retrieved Data as CSV",
                    data=csv_data,
                    file_name=f"experiment_{selected_id}.csv",
                    mime="text/csv"
                )

                # DOWNLOAD COMPLETE EXPERIMENT REPORT AS EXCEL

                all_model_results = get_model_results()

                if (
                    all_model_results is not None
                    and "experiment_id" in all_model_results.columns
                ):
                    history_model_results = all_model_results[
                        all_model_results["experiment_id"] == selected_id
                    ].copy()
                else:
                    history_model_results = pd.DataFrame()

                experiment_details_df = selected_experiment.to_frame().T

                excel_report = create_excel_workbook({
                    "Experiment Details": experiment_details_df,
                    "Growth Data": growth_data,
                    "Model Results": history_model_results
                })

                st.download_button(
                    "Download Complete Experiment Report (Excel)",
                    data=excel_report,
                    file_name=f"experiment_{selected_id}_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"history_excel_{selected_id}"
                )

            else:
                st.warning(
                    "No experiments match your search."
                )

    except Exception as error:
        st.error(
            f"Could not retrieve experiment history: {error}"
        )


# =====================================================
# PAGE 3: EXPERIMENT COMPARISON
# =====================================================

elif page == "Experiment Comparison":

    st.header("📊 Experiment Comparison Dashboard")

    st.write("""
    Compare different saved microbial growth experiments,
    growth parameters and mathematical model performance.
    """)

    try:
        experiments = get_experiments()
        model_results = get_model_results()
        st.write("Model result columns:", model_results.columns.tolist())
        st.dataframe(model_results)

        if experiments.empty:
            st.info("No saved experiments are available.")

        elif model_results.empty:
            st.info("No saved model results are available.")

        else:
            st.subheader("1. Select Experiments")

            selected_ids = st.multiselect(
                "Choose experiments to compare",
                options=experiments["experiment_id"].tolist(),
                default=experiments["experiment_id"].tolist()[
                    :min(3, len(experiments))
                ],
                format_func=lambda x: (
                    f"Experiment {x} - "
                    + str(
                        experiments.loc[
                            experiments["experiment_id"] == x,
                            "organism_name"
                        ].iloc[0]
                    )
                )
            )

            if not selected_ids:
                st.warning("Please select at least one experiment.")

            else:
                selected_experiments = experiments[
                    experiments["experiment_id"].isin(selected_ids)
                ].copy()

                selected_results = model_results[
                    model_results["experiment_id"].isin(selected_ids)
                ].copy()

                st.subheader("2. Selected Experiment Details")

                st.dataframe(
                    selected_experiments,
                    use_container_width=True,
                    hide_index=True
                )

                if selected_results.empty:
                    st.warning(
                        "No model results found for the selected experiments."
                    )

                else:
                    comparison_table = selected_results.merge(
                        experiments[
                            ["experiment_id", "organism_name"]
                        ],
                        on="experiment_id",
                        how="left"
                    )

                    st.subheader("3. Model Results Comparison")

                    display_columns = [
                        "experiment_id",
                        "organism_name",
                        "model_name",
                        "maximum_fitted_od",
                        "maximum_growth_rate",
                        "lag_time",
                        "r_squared",
                        "rmse",
                        "aic",
                        "aicc"
                    ]

                    st.dataframe(
                        comparison_table[display_columns].round(5),
                        use_container_width=True,
                        hide_index=True
                    )

                    # MODEL PERFORMANCE CHART

                    st.subheader("4. Statistical Performance Comparison")

                    metric_choice = st.selectbox(
                        "Select statistical metric",
                        [
                            "r_squared",
                            "rmse",
                            "aic",
                            "aicc"
                        ],
                        format_func=lambda x: {
                            "r_squared": "R²",
                            "rmse": "RMSE",
                            "aic": "AIC",
                            "aicc": "AICc"
                        }[x]
                    )

                    metric_data = selected_results.dropna(
                        subset=[metric_choice]
                    )

                    if not metric_data.empty:

                        metric_figure = go.Figure()

                        for model_name in metric_data[
                            "model_name"
                        ].unique():

                            model_data = metric_data[
                                metric_data["model_name"] == model_name
                            ]

                            metric_figure.add_trace(go.Bar(
                                x=[
                                    f"Experiment {value}"
                                    for value in model_data["experiment_id"]
                                ],
                                y=model_data[metric_choice],
                                name=model_name
                            ))

                        metric_figure.update_layout(
                            title=f"{metric_choice.upper()} Comparison",
                            xaxis_title="Experiment",
                            yaxis_title=metric_choice.upper(),
                            barmode="group"
                        )

                        st.plotly_chart(
                            metric_figure,
                            use_container_width=True
                        )

                    else:
                        st.info("No valid values for this metric.")

                    # PARAMETER COMPARISON

                    st.subheader("5. Growth Parameter Comparison")

                    parameter_choice = st.selectbox(
                        "Select growth parameter",
                        [
                            "maximum_fitted_od",
                            "maximum_growth_rate",
                            "lag_time"
                        ],
                        format_func=lambda x: {
                            "maximum_fitted_od": "Maximum fitted OD",
                            "maximum_growth_rate": "Maximum growth rate",
                            "lag_time": "Lag time"
                        }[x]
                    )

                    parameter_figure = go.Figure()

                    for model_name in selected_results[
                        "model_name"
                    ].unique():

                        model_data = selected_results[
                            selected_results["model_name"] == model_name
                        ]

                        parameter_figure.add_trace(go.Bar(
                            x=[
                                f"Experiment {value}"
                                for value in model_data["experiment_id"]
                            ],
                            y=model_data[parameter_choice],
                            name=model_name
                        ))

                    parameter_figure.update_layout(
                        title="Growth Parameter Comparison",
                        xaxis_title="Experiment",
                        yaxis_title=parameter_choice.replace(
                            "_", " "
                        ).title(),
                        barmode="group"
                    )

                    st.plotly_chart(
                        parameter_figure,
                        use_container_width=True
                    )

                    # DOWNLOAD COMPARISON

                    st.subheader("6. Download Comparison Results")

                    download_data = comparison_table[
                        display_columns
                    ].to_csv(index=False)

                    st.download_button(
                        "Download Comparison as CSV",
                        data=download_data,
                        file_name="microbial_experiment_comparison.csv",
                        mime="text/csv"
                    )

                    # DOWNLOAD COMPARISON REPORT AS EXCEL

                    comparison_growth_frames = []

                    for experiment_id in selected_ids:

                        one_growth_data = get_growth_data(
                            experiment_id
                        ).copy()

                        one_growth_data.insert(
                            0,
                            "experiment_id",
                            experiment_id
                        )

                        comparison_growth_frames.append(
                            one_growth_data
                        )

                    if comparison_growth_frames:
                        comparison_growth_data = pd.concat(
                            comparison_growth_frames,
                            ignore_index=True
                        )
                    else:
                        comparison_growth_data = pd.DataFrame()

                    comparison_excel = create_excel_workbook({
                        "Selected Experiments": selected_experiments,
                        "Model Comparison": comparison_table[display_columns],
                        "Growth Data": comparison_growth_data
                    })

                    st.download_button(
                        "Download Complete Comparison Report (Excel)",
                        data=comparison_excel,
                        file_name="microbial_experiment_comparison.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="comparison_excel_download"
                    )

                    st.caption("""
                    Interpretation: Higher R² and lower RMSE, AIC and AICc
                    can indicate better statistical fit under comparable
                    conditions. Model selection should also consider
                    residual patterns and scientific plausibility.
                    Comparisons across different datasets or OD scales
                    require care.
                    """)

    except Exception as error:
        st.error(
            f"Could not load experiment comparison: {error}"
        )


# =====================================================
# FOOTER
# =====================================================

st.divider()

st.caption(
    "Microbial Kinetics Research Hub | "
    "Integrated Growth Analysis and Comparative Database"
)
