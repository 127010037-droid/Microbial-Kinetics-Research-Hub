
import numpy as np
from scipy.optimize import curve_fit
from scipy.stats import t

from models import (
    logistic_model,
    gompertz_model,
    baranyi_model
)


def calculate_metrics(actual, predicted, parameter_count):

    residuals = actual - predicted

    rss = np.sum(residuals ** 2)
    rmse = np.sqrt(np.mean(residuals ** 2))

    total_sum = np.sum(
        (actual - np.mean(actual)) ** 2
    )

    r2 = (
        1 - rss / total_sum
        if total_sum > 0 else np.nan
    )

    n = len(actual)

    aic = (
        n * np.log(max(rss / n, 1e-15))
        + 2 * parameter_count
    )

    aicc = (
        aic + (
            2 * parameter_count * (parameter_count + 1)
        ) / (n - parameter_count - 1)
        if n > parameter_count + 1
        else np.nan
    )

    return {
        "RMSE": rmse,
        "R2": r2,
        "AIC": aic,
        "AICc": aicc,
        "RSS": rss
    }


def calculate_confidence_intervals(
    parameters,
    covariance,
    n,
    confidence=0.95
):

    degrees_of_freedom = n - len(parameters)

    if degrees_of_freedom <= 0:
        return None

    standard_errors = np.sqrt(
        np.maximum(np.diag(covariance), 0)
    )

    critical_value = t.ppf(
        (1 + confidence) / 2,
        degrees_of_freedom
    )

    lower = parameters - critical_value * standard_errors
    upper = parameters + critical_value * standard_errors

    return {
        "standard_errors": standard_errors,
        "lower": lower,
        "upper": upper
    }


def fit_growth_models(time, od):

    time = np.asarray(time, dtype=float)
    od = np.asarray(od, dtype=float)

    valid = np.isfinite(time) & np.isfinite(od)

    time = time[valid]
    od = od[valid]

    if len(time) < 5:
        raise ValueError(
            "At least 5 valid data points are required."
        )

    if np.any(od < 0):
        raise ValueError("OD values cannot be negative.")

    order = np.argsort(time)

    time = time[order]
    od = od[order]

    if len(np.unique(time)) != len(time):
        raise ValueError("Time values must be unique.")

    if np.ptp(time) <= 0 or np.ptp(od) <= 0:
        raise ValueError(
            "Time and OD values must show variation."
        )

    duration = np.ptp(time)
    maximum_od = max(np.max(od), 0.01)

    initial_guess = [
        maximum_od * 1.2,
        1.0 / duration,
        time[0] + duration * 0.2
    ]

    lower_bounds = [
        max(maximum_od * 0.5, 1e-6),
        1e-6,
        time[0] - duration
    ]

    upper_bounds = [
        maximum_od * 100,
        10.0 / duration,
        time[-1]
    ]

    models = {
        "Logistic": logistic_model,
        "Gompertz": gompertz_model,
        "Baranyi": baranyi_model
    }

    results = {}

    for name, model in models.items():

        try:

            parameters, covariance = curve_fit(
                model,
                time,
                od,
                p0=initial_guess,
                bounds=(lower_bounds, upper_bounds),
                maxfev=50000
            )

            predicted = model(time, *parameters)

            residuals = od - predicted

            metrics = calculate_metrics(
                od,
                predicted,
                len(parameters)
            )

            confidence_intervals = (
                calculate_confidence_intervals(
                    parameters,
                    covariance,
                    len(time)
                )
            )

            results[name] = {
                "parameters": {
                    "Maximum fitted OD": parameters[0],
                    "Maximum growth rate": parameters[1],
                    "Lag time": parameters[2]
                },

                "standard_errors": (
                    confidence_intervals["standard_errors"]
                    if confidence_intervals else None
                ),

                "confidence_intervals": (
                    confidence_intervals
                ),

                "predicted": predicted,
                "residuals": residuals,
                "metrics": metrics,
                "success": True
            }

        except (
            RuntimeError,
            ValueError,
            FloatingPointError
        ) as error:

            results[name] = {
                "success": False,
                "error": str(error)
            }

    return results
