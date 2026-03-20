"""Polls ESPN scoreboard API and tracks NCAA tournament team states."""

import requests
import time
from dataclasses import dataclass, field
from datetime import datetime

ESPN_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/basketball/"
    "mens-college-basketball/scoreboard?dates={date}&groups=100&limit=100"
)

TOURNAMENT_DATES = [
    "20260319", "20260320",  # Round 1
    "20260321", "20260322",  # Round 2
    "20260326", "20260327",  # Sweet 16
    "20260328", "20260329",  # Elite 8
    "20260404",              # Final Four
    "20260406",              # Championship
]

# Points awarded for winning in each round
ROUND_WIN_POINTS = {
    "1st Round": 1,
    "2nd Round": 2,
    "Sweet 16": 3,
    "Elite 8": 4,
    "Final Four": 5,
    "National Championship": 6,
}

MAX_POINTS = 21

# Status constants
STATUS_FINAL = "STATUS_FINAL"
STATUS_IN_PROGRESS = "STATUS_IN_PROGRESS"
STATUS_SCHEDULED = "STATUS_SCHEDULED"
STATUS_HALFTIME = "STATUS_HALFTIME"

IN_PROGRESS_STATUSES = {STATUS_IN_PROGRESS, STATUS_HALFTIME, "STATUS_END_PERIOD"}


@dataclass
class TeamState:
    name: str
    seed: int = 0
    status: str = "alive"  # alive, eliminated, playing
    points_earned: int = 0
    max_remaining: int = MAX_POINTS
    current_score: str = ""
    opponent: str = ""
    opponent_score: str = ""
    game_status: str = ""
    game_detail: str = ""  # e.g. "Half", "2nd 12:34"


class ESPNClient:
    def __init__(self):
        self.team_states: dict[str, TeamState] = {}
        self.last_poll: datetime | None = None
        self._cache: dict[str, tuple[float, dict]] = {}
        self._cache_ttl = 30  # seconds

    def get_team_states(self) -> dict[str, TeamState]:
        return self.team_states

    def poll(self):
        """Poll all tournament dates and rebuild team states."""
        all_games = []
        for date in TOURNAMENT_DATES:
            events = self._fetch_date(date)
            all_games.extend(events)

        self._process_games(all_games)
        self.last_poll = datetime.now()

    def _fetch_date(self, date: str) -> list[dict]:
        now = time.time()
        if date in self._cache:
            cached_time, cached_data = self._cache[date]
            if now - cached_time < self._cache_ttl:
                return cached_data

        try:
            resp = requests.get(ESPN_URL.format(date=date), timeout=10)
            resp.raise_for_status()
            data = resp.json()
            events = data.get("events", [])
            self._cache[date] = (now, events)
            return events
        except Exception as e:
            print(f"ESPN fetch error for {date}: {e}")
            # Return cached data if available, even if stale
            if date in self._cache:
                return self._cache[date][1]
            return []

    def _process_games(self, events: list[dict]):
        states: dict[str, TeamState] = {}

        for event in events:
            comp = event["competitions"][0]
            game_status = comp["status"]["type"]["name"]
            game_detail = comp["status"].get("type", {}).get("shortDetail", "")

            # Extract round from notes
            round_name = ""
            notes = event.get("notes", comp.get("notes", []))
            for note in notes:
                headline = note.get("headline", "")
                if headline:
                    parts = headline.split(" - ")
                    round_name = parts[-1].strip()
                    break

            competitors = comp["competitors"]
            if len(competitors) != 2:
                continue

            # Build competitor info
            team_infos = []
            for c in competitors:
                location = c["team"]["location"]
                if location == "TBD":
                    break
                team_infos.append({
                    "name": location,
                    "seed": c.get("curatedRank", {}).get("current", 0),
                    "score": c.get("score", "0"),
                    "winner": c.get("winner"),
                    "home_away": c.get("homeAway", ""),
                })
            else:
                # Only process if we didn't break (no TBD teams)
                self._process_matchup(
                    states, team_infos, game_status, game_detail, round_name
                )

        self.team_states = states

    def _process_matchup(
        self,
        states: dict[str, TeamState],
        team_infos: list[dict],
        game_status: str,
        game_detail: str,
        round_name: str,
    ):
        t0, t1 = team_infos[0], team_infos[1]

        for me, opp in [(t0, t1), (t1, t0)]:
            name = me["name"]
            if name not in states:
                states[name] = TeamState(name=name, seed=me["seed"])

            state = states[name]

            if game_status == STATUS_FINAL:
                pts = ROUND_WIN_POINTS.get(round_name, 0)
                if me["winner"] is True:
                    state.points_earned += pts
                    state.status = "alive"
                elif me["winner"] is False:
                    state.status = "eliminated"
                    state.max_remaining = 0

            elif game_status in IN_PROGRESS_STATUSES:
                state.status = "playing"
                state.current_score = me["score"]
                state.opponent = opp["name"]
                state.opponent_score = opp["score"]
                state.game_status = game_status
                state.game_detail = game_detail

            elif game_status == STATUS_SCHEDULED:
                if state.status not in ("eliminated", "playing"):
                    state.status = "alive"
                state.opponent = opp["name"]

        # Update max_remaining for alive/playing teams
        for name in [t0["name"], t1["name"]]:
            s = states[name]
            if s.status != "eliminated":
                s.max_remaining = MAX_POINTS - s.points_earned
