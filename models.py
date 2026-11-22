
import numpy as np

def logistic_model(t, A, mu_max, lag):
    """
    Logistic microbial growth model.
    A       = Maximum fitted OD
    mu_max  = Maximum specific growth rate
    lag     = Lag time
    """
    t = np.asarray(t, dtype=float)

    exponent = 1 + np.exp(
        4 * mu_max * (lag - t) / A
    )

    return A / exponent


def gompertz_model(t, A, mu_max, lag):
    """
    Modified Gompertz microbial growth model.
    A       = Maximum fitted OD
    mu_max  = Maximum specific growth rate
    lag     = Lag time
    """
    t = np.asarray(t, dtype=float)

    exponent = np.exp(
        (mu_max * np.e / A) * (lag - t) + 1
    )

    return A * np.exp(-exponent)


def baranyi_model(t, A, mu_max, lag):
    """
    Simplified Baranyi-Roberts growth model.
    A       = Maximum fitted OD
    mu_max  = Maximum specific growth rate
    lag     = Approximate lag time
    """
    t = np.asarray(t, dtype=float)

    h0 = mu_max * lag
    q0 = 1 / (np.exp(h0) - 1 + 1e-12)

    adjustment = t + (
        np.log1p(np.exp(-mu_max * t) + q0)
        - np.log1p(q0)
    ) / mu_max

    exponent = 4 + (
        4 * mu_max / A
    ) * (lag - adjustment)

    exponent = np.clip(exponent, -500, 500)

    return A / (1 + np.exp(exponent))
