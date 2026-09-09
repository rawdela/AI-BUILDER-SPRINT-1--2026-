import os
import threading
import traceback
from pathlib import Path

from flask import Flask, jsonify, render_template, send_file

from app import run_all_applicants

app = Flask(__name__)

STATE = {
    "status": "idle",
    "message": "Ready to run.",
    "result": None,
    "error": None,
}
STATE_LOCK = threading.Lock()


def progress(message):
    with STATE_LOCK:
        STATE["message"] = message


def run_demo():
    with STATE_LOCK:
        STATE["status"] = "running"
        STATE["error"] = None
        STATE["result"] = None
        STATE["message"] = "Connecting to the AI models…"

    try:
        result = run_all_applicants(progress_callback=progress)
        with STATE_LOCK:
            STATE["result"] = result
            STATE["status"] = "complete"
            STATE["message"] = "Simulation complete — all dossiers and the final decision are ready."
    except Exception as exc:
        with STATE_LOCK:
            STATE["status"] = "error"
            STATE["error"] = str(exc)
            STATE["message"] = "The AI request could not be completed. You can retry safely."
        traceback.print_exc()


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/run")
def start_run():
    with STATE_LOCK:
        if STATE["status"] == "running":
            return jsonify({"ok": False, "message": "A simulation is already running."}), 409

    thread = threading.Thread(target=run_demo, daemon=True)
    thread.start()
    return jsonify({"ok": True})


@app.get("/api/status")
def status():
    with STATE_LOCK:
        return jsonify(dict(STATE))


@app.get("/api/results")
def results():
    with STATE_LOCK:
        result = STATE["result"]
    if not result:
        return jsonify({"ok": False, "message": "No results yet."}), 404
    return jsonify(result)


@app.get("/api/download")
def download_results():
    path = Path("last_seat_results.json")
    if not path.exists():
        return jsonify({"ok": False, "message": "Run the simulation first."}), 404
    return send_file(path, as_attachment=True, download_name="last_seat_results.json")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
