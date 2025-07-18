def get_rps_history():
    """
    Probably retrieves the historical RPS data with a query to Nginx Exporter
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
    return 1000
