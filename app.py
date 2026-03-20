"""Flask application for the Marshall Gramm NCAA Pool Tracker."""

import os
import threading
import time
from datetime import datetime

from flask import Flask, render_template, jsonify, abort

from data_loader import load_rosters
from espn_client import ESPNClient
from scoring import compute_leaderboard, compute_highlights

app = Flask(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "NCAA_2026_Teams.xlsx")

rosters = None
espn = None


def init_app():
    global rosters, espn
    rosters = load_rosters(DATA_PATH)
    espn = ESPNClient()
    espn.poll()
    print(f"Loaded {len(rosters)} participants, {len(espn.team_states)} teams tracked")


def poll_loop():
    while True:
        time.sleep(30)
        try:
            espn.poll()
        except Exception as e:
            print(f"ESPN poll error: {e}")


@app.route("/")
def leaderboard():
    states = espn.get_team_states()
    entries = compute_leaderboard(rosters, states)
    highlights = compute_highlights(entries)
    return render_template(
        "leaderboard.html",
        entries=entries,
        highlights=highlights,
        last_updated=espn.last_poll,
    )


@app.route("/participant/<name>")
def participant_detail(name):
    if name not in rosters:
        abort(404)
    states = espn.get_team_states()
    entries = compute_leaderboard(rosters, states)
    entry = next((e for e in entries if e["name"] == name), None)
    if not entry:
        abort(404)
    return render_template(
        "participant.html",
        entry=entry,
        participant=rosters[name],
        last_updated=espn.last_poll,
    )


@app.route("/api/leaderboard")
def api_leaderboard():
    states = espn.get_team_states()
    entries = compute_leaderboard(rosters, states)
    highlights = compute_highlights(entries)
    return jsonify(
        entries=entries,
        highlights=highlights,
        last_updated=espn.last_poll.isoformat() if espn.last_poll else None,
    )


init_app()
t = threading.Thread(target=poll_loop, daemon=True)
t.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
