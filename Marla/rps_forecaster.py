def update_rps_history(new_rps):
    """
    Maintains a rolling history of RPS values to be used in ARIMA training.
    """

def train_arima_model():
    """
    Trains (or updates) the ARIMA model using the current RPS history.
    Only called periodically or after enough data is available.
    """

def predict_next_rps():
    """
    Uses the trained ARIMA model to forecast the next-minute RPS.
    Returns: int
    """
