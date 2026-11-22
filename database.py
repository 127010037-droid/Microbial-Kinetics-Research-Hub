
import os
import mysql.connector
import pandas as pd
import numpy as np
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


# =====================================================
# 1. DATABASE CONNECTION
# =====================================================

def get_connection():

    try:
        config = st.secrets["mysql"]
    except Exception as e:
        raise RuntimeError(
            f"Streamlit cannot read the [mysql] Secrets section: {e}"
        )

    ca_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "isrgrootx1.pem"
    )

    if not os.path.exists(ca_path):
        raise FileNotFoundError("isrgrootx1.pem is missing.")

    return mysql.connector.connect(
        host=config["host"],
        port=int(config.get("port", 4000)),
        user=config["user"],
        password=config["password"],
        database=config["database"],
        ssl_ca=ca_path,
        ssl_verify_cert=True,
        ssl_verify_identity=True,
        connection_timeout=20
    )


# =====================================================
# 2. CREATE DATABASE TABLES
# =====================================================

def create_tables():

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                experiment_id INT AUTO_INCREMENT PRIMARY KEY,
                organism_name VARCHAR(150) NOT NULL,
                strain_name VARCHAR(150),
                temperature FLOAT,
                ph FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS growth_data (
                data_id INT AUTO_INCREMENT PRIMARY KEY,
                experiment_id INT NOT NULL,
                time_value FLOAT NOT NULL,
                od_value FLOAT NOT NULL,
                FOREIGN KEY (experiment_id)
                    REFERENCES experiments(experiment_id)
                    ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_results (
                result_id INT AUTO_INCREMENT PRIMARY KEY,
                experiment_id INT NOT NULL,
                model_name VARCHAR(50) NOT NULL,
                maximum_fitted_od FLOAT,
                maximum_growth_rate FLOAT,
                lag_time FLOAT,
                r_squared FLOAT,
                rmse FLOAT,
                aic FLOAT,
                aicc FLOAT,
                FOREIGN KEY (experiment_id)
                    REFERENCES experiments(experiment_id)
                    ON DELETE CASCADE
            )
        """)

        conn.commit()

    finally:
        cursor.close()
        conn.close()


# =====================================================
# 3. SAVE EXPERIMENT DETAILS
# =====================================================

def save_experiment(organism, strain, temperature, ph):

    conn = get_connection()
    cursor = conn.cursor()

    try:
        query = """
            INSERT INTO experiments
            (organism_name, strain_name, temperature, ph)
            VALUES (%s, %s, %s, %s)
        """

        cursor.execute(
            query,
            (organism, strain, temperature, ph)
        )

        experiment_id = cursor.lastrowid
        conn.commit()

        return experiment_id

    finally:
        cursor.close()
        conn.close()


# =====================================================
# 4. SAVE GROWTH DATA
# =====================================================

def save_growth_data(experiment_id, data):

    conn = get_connection()
    cursor = conn.cursor()

    try:
        query = """
            INSERT INTO growth_data
            (experiment_id, time_value, od_value)
            VALUES (%s, %s, %s)
        """

        if isinstance(data, pd.DataFrame):
            rows = [
                (
                    experiment_id,
                    float(row["Time"]),
                    float(row["OD"])
                )
                for _, row in data.iterrows()
            ]
        else:
            rows = [
                (
                    experiment_id,
                    float(row["Time"]),
                    float(row["OD"])
                )
                for row in data
            ]

        if rows:
            cursor.executemany(query, rows)

        conn.commit()

    finally:
        cursor.close()
        conn.close()


# =====================================================
# 5. GET ALL EXPERIMENTS
# =====================================================

def get_experiments():

    conn = get_connection()

    try:
        query = """
            SELECT *
            FROM experiments
            ORDER BY created_at DESC
        """

        return pd.read_sql(query, conn)

    finally:
        conn.close()


# =====================================================
# 6. GET GROWTH DATA
# =====================================================

def get_growth_data(experiment_id):

    conn = get_connection()

    try:
        query = """
            SELECT
                time_value AS Time,
                od_value AS OD
            FROM growth_data
            WHERE experiment_id = %s
            ORDER BY time_value
        """

        return pd.read_sql(
            query,
            conn,
            params=(experiment_id,)
        )

    finally:
        conn.close()


# =====================================================
# 7. GET ALL MODEL RESULTS
# =====================================================

def get_model_results():

    conn = get_connection()

    try:
        query = """
            SELECT *
            FROM model_results
            ORDER BY result_id DESC
        """

        return pd.read_sql(query, conn)

    finally:
        conn.close()


# =====================================================
# 8. SAVE MODEL RESULTS
# =====================================================

def save_model_results(experiment_id, results):

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO model_results (
            experiment_id,
            model_name,
            maximum_fitted_od,
            maximum_growth_rate,
            lag_time,
            r_squared,
            rmse,
            aic,
            aicc
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    def clean_value(value):

        if value is None:
            return None

        try:
            value = float(value)

            if np.isfinite(value):
                return value

            return None

        except (TypeError, ValueError):
            return None

    rows = []

    try:

        if isinstance(results, dict):

            for model_name, result in results.items():

                if not isinstance(result, dict):
                    continue

                if not result.get("success", False):
                    continue

                parameters = result.get("parameters", {})
                metrics = result.get("metrics", {})

                rows.append((
                    experiment_id,
                    str(model_name),

                    clean_value(
                        parameters.get("Maximum fitted OD")
                    ),

                    clean_value(
                        parameters.get("Maximum growth rate")
                    ),

                    clean_value(
                        parameters.get("Lag time")
                    ),

                    clean_value(metrics.get("R2")),
                    clean_value(metrics.get("RMSE")),
                    clean_value(metrics.get("AIC")),
                    clean_value(metrics.get("AICc"))
                ))

        if rows:
            cursor.executemany(query, rows)
            conn.commit()

        if not rows:
            raise ValueError(
                "No successful model results were available to save."
            )

    finally:
        cursor.close()
        conn.close()
