
import os
import mysql.connector
import pandas as pd
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

    st.write("Cloud database settings detected.")
    st.write("Host:", config.get("host", "MISSING"))
    st.write("Port:", config.get("port", "MISSING"))

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

    # Local MySQL connection using .env
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE", "microbial_growth_db"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        connection_timeout=20
    )


# =====================================================
# 2. CREATE DATABASE TABLES
# =====================================================

def create_tables():

    conn = get_connection()
    cursor = conn.cursor()

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
    cursor.close()
    conn.close()


# =====================================================
# 3. SAVE EXPERIMENT DETAILS
# =====================================================

def save_experiment(organism, strain, temperature, ph):

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO experiments
        (organism_name, strain_name, temperature, ph)
        VALUES (%s, %s, %s, %s)
    """

    values = (organism, strain, temperature, ph)

    cursor.execute(query, values)

    experiment_id = cursor.lastrowid

    conn.commit()
    cursor.close()
    conn.close()

    return experiment_id


# =====================================================
# 4. SAVE GROWTH DATA
# =====================================================

def save_growth_data(experiment_id, data):

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO growth_data
        (experiment_id, time_value, od_value)
        VALUES (%s, %s, %s)
    """

    if isinstance(data, pd.DataFrame):
        rows = [
            (experiment_id, float(row["Time"]), float(row["OD"]))
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
    cursor.close()
    conn.close()


# =====================================================
# 5. GET ALL EXPERIMENTS
# =====================================================

def get_experiments():

    conn = get_connection()

    query = """
        SELECT *
        FROM experiments
        ORDER BY created_at DESC
    """

    df = pd.read_sql(query, conn)

    conn.close()

    return df


# =====================================================
# 6. GET GROWTH DATA FOR AN EXPERIMENT
# =====================================================

def get_growth_data(experiment_id):

    conn = get_connection()

    query = """
        SELECT
            time_value AS Time,
            od_value AS OD
        FROM growth_data
        WHERE experiment_id = %s
        ORDER BY time_value
    """

    df = pd.read_sql(
        query,
        conn,
        params=(experiment_id,)
    )

    conn.close()

    return df


# =====================================================
# 7. GET ALL MODEL RESULTS
# =====================================================

def get_model_results():

    conn = get_connection()

    query = """
        SELECT *
        FROM model_results
        ORDER BY result_id DESC
    """

    df = pd.read_sql(query, conn)

    conn.close()

    return df


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

    def get_value(metrics, possible_names):

        normalized = {
            str(key).lower().replace(" ", "").replace("_", "").replace("²", "2"):
            value
            for key, value in metrics.items()
        }

        for name in possible_names:
            key = name.lower().replace(" ", "").replace("_", "").replace("²", "2")
            if key in normalized:
                return normalized[key]

        return None

    rows = []

    if isinstance(results, pd.DataFrame):
        result_items = [
            (str(row.get("model_name", row.get("Model", "Unknown"))), row.to_dict())
            for _, row in results.iterrows()
        ]

    elif isinstance(results, dict):
        if any(key in results for key in ["model_name", "Model", "model"]):
            result_items = [
                (
                    str(results.get("model_name", results.get("Model", results.get("model", "Unknown")))),
                    results
                )
            ]
        else:
            result_items = list(results.items())

    else:
        result_items = []

    for model_name, metrics in result_items:

        if not isinstance(metrics, dict):
            continue

        rows.append((
            experiment_id,
            str(model_name),
            get_value(metrics, ["maximum_fitted_od", "Maximum Fitted OD", "max_od"]),
            get_value(metrics, ["maximum_growth_rate", "Maximum Growth Rate", "mu_max"]),
            get_value(metrics, ["lag_time", "Lag Time", "lambda"]),
            get_value(metrics, ["r_squared", "R2", "R²"]),
            get_value(metrics, ["rmse", "RMSE"]),
            get_value(metrics, ["aic", "AIC"]),
            get_value(metrics, ["aicc", "AICc"])
        ))

    if rows:
        cursor.executemany(query, rows)

    conn.commit()
    cursor.close()
    conn.close()
