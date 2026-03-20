"""Flask application for the Marshall Gramm NCAA Pool Tracker."""

import os
import time

from flask import Flask, render_template, jsonify, abort

from data_loader import load_rosters
from espn_client import ESPNClient
from scoring import compute_leaderboard, compute_highlights

app = Flask(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "NCAA_2026_Teams.xlsx")

POLL_INTERVAL = 30  # seconds between ESPN API refreshes

rosters = load_rosters(DATA_PATH)
espn = ESPNClient()
_last_poll_time = 0


def ensure_fresh():
    """Re-poll ESPN if data is stale. Called on each request."""
    global _last_poll_time
    now = time.time()
    if now - _last_poll_time >= POLL_INTERVAL:
        try:
            espn.poll()
        except Exception as e:
            print(f"ESPN poll error: {e}")
        _last_poll_time = time.time()


@app.route("/")
def leaderboard():
    ensure_fresh()
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
    ensure_fresh()
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
    ensure_fresh()
    states = espn.get_team_states()
    entries = compute_leaderboard(rosters, states)
    highlights = compute_highlights(entries)
    return jsonify(
        entries=entries,
        highlights=highlights,
        last_updated=espn.last_poll.isoformat() if espn.last_poll else None,
    )


print(f"Loaded {len(rosters)} participants")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
