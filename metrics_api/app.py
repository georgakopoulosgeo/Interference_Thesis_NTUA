from flask import Flask, jsonify, Response
from pcm_reader import init_metrics_updater, metrics_to_csv, BUFFER_PATH

app = Flask(__name__)
cache = init_metrics_updater(BUFFER_PATH)

@app.route("/metrics_list", methods=["GET"])
def get_metrics():
    """Returns last parsed PCM metrics from buffer."""
    return jsonify({"metrics": cache["metrics"]})

@app.route("/metrics", methods=["GET"])
def get_metrics_csv():
    csv_data = metrics_to_csv(cache["metrics"])
    return Response(csv_data, mimetype="text/csv")

@app.route("/health", methods=["GET"])
def health():
    """Simple health check endpoint."""
    return jsonify({"status": "ok", "metrics_count": len(cache["metrics"])})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=30090, threaded=True)
