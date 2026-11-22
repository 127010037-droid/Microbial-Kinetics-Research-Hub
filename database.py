import os
import mysql.connector
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


# DATABASE CONNECTION

def get_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )


# CREATE TABLES

def create_tables():

    connection = get_connection()
    cursor = connection.cursor()

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

    connection.commit()
    cursor.close()
    connection.close()


# SAVE EXPERIMENT

def save_experiment(organism, strain, temperature, ph):

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO experiments
            (organism_name, strain_name, temperature, ph)
            VALUES (%s, %s, %s, %s)
        """, (organism, strain, temperature, ph))

        experiment_id = cursor.lastrowid
        connection.commit()

        return experiment_id

    finally:
        cursor.close()
        connection.close()


# SAVE GROWTH DATA

def save_growth_data(experiment_id, data):

    connection = get_connection()
    cursor = connection.cursor()

    try:
        records = [
            (
                experiment_id,
                float(row["Time"]),
                float(row["OD"])
            )
            for _, row in data.iterrows()
        ]

        cursor.executemany("""
            INSERT INTO growth_data
            (experiment_id, time_value, od_value)
            VALUES (%s, %s, %s)
        """, records)

        connection.commit()

    finally:
        cursor.close()
        connection.close()


# GET ALL EXPERIMENTS

def get_experiments():

    connection = get_connection()

    try:
        query = """
            SELECT
                experiment_id,
                organism_name,
                strain_name,
                temperature,
                ph,
                created_at
            FROM experiments
            ORDER BY created_at DESC
        """

        return pd.read_sql(query, connection)

    finally:
        connection.close()


# GET GROWTH DATA

def get_growth_data(experiment_id):

    connection = get_connection()

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
            connection,
            params=(experiment_id,)
        )

    finally:
        connection.close()


# GET SAVED MODEL RESULTS

def get_model_results():

    connection = get_connection()

    try:
        query = """
            SELECT
                result_id,
                experiment_id,
                model_name,
                maximum_fitted_od,
                maximum_growth_rate,
                lag_time,
                r_squared,
                rmse,
                aic,
                aicc
            FROM model_results
            ORDER BY experiment_id, model_name
        """

        return pd.read_sql(query, connection)

    finally:
        connection.close()


# SAVE MODEL RESULTS

def save_model_results(experiment_id, results):

    connection = get_connection()
    cursor = connection.cursor()

    try:
        for model_name, result in results.items():

            if not result.get("success", False):
                continue

            parameters = result["parameters"]
            metrics = result["metrics"]

            cursor.execute("""
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
            """, (
                experiment_id,
                model_name,
                parameters["Maximum fitted OD"],
                parameters["Maximum growth rate"],
                parameters["Lag time"],
                metrics["R2"],
                metrics["RMSE"],
                metrics["AIC"],
                metrics["AICc"]
            ))

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()