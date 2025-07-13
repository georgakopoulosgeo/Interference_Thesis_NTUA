from flask import Flask, jsonify
from pcm_reader import init_metrics_updater, BUFFER_PATH

app = Flask(__name__)
cache = init_metrics_updater(BUFFER_PATH)


@app.route("/metrics", methods=["GET"])
def get_metrics():
    """Returns last parsed PCM metrics from buffer."""
    return jsonify({"metrics":cache["metrics"]})


@app.route("/health", methods=["GET"])
def health():
    """Simple health check endpoint."""
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
