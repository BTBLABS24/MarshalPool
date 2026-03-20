"""Computes leaderboard and highlight stats from rosters + team states."""

from data_loader import Participant, TeamPick
from espn_client import TeamState, MAX_POINTS


def compute_leaderboard(
    participants: dict[str, Participant],
    team_states: dict[str, TeamState],
) -> list[dict]:
    entries = []

    for name, p in participants.items():
        points = 0
        alive = 0
        eliminated = 0
        max_possible = 0
        teams_detail = []

        dollars_alive = 0

        for pick in p.picks:
            state = team_states.get(pick.team)
            if state is None:
                # Team hasn't appeared in any game yet - still alive
                alive += 1
                pts = 0
                mx = MAX_POINTS
                dollars_alive += pick.cost
            elif state.status == "eliminated":
                eliminated += 1
                pts = state.points_earned
                mx = 0
            else:
                alive += 1
                pts = state.points_earned
                mx = state.max_remaining
                dollars_alive += pick.cost

            points += pts
            max_possible += pts + mx
            teams_detail.append({
                "team": pick.team,
                "seed": pick.seed,
                "cost": pick.cost,
                "status": state.status if state else "scheduled",
                "points": pts,
                "max_remaining": mx,
                "current_score": state.current_score if state else "",
                "opponent": state.opponent if state else "",
                "opponent_score": state.opponent_score if state else "",
                "game_detail": state.game_detail if state else "",
            })

        entries.append({
            "name": name,
            "first": p.first,
            "last": p.last,
            "points": points,
            "alive": alive,
            "eliminated": eliminated,
            "max_possible": max_possible,
            "num_teams": len(p.picks),
            "dollars_alive": dollars_alive,
            "total_cost": p.total_cost,
            "teams": teams_detail,
        })

    # Sort: points desc, then max_possible desc
    entries.sort(key=lambda e: (-e["points"], -e["max_possible"]))

    # Assign ranks with ties
    for i, entry in enumerate(entries):
        if i == 0 or entry["points"] != entries[i - 1]["points"]:
            entry["rank"] = i + 1
        else:
            entry["rank"] = entries[i - 1]["rank"]

    return entries


def compute_highlights(entries: list[dict]) -> dict:
    """Compute top-of-page highlight cards."""
    if not entries:
        return {}

    leader = entries[0]
    projected = max(entries, key=lambda e: e["dollars_alive"])

    return {
        "leader": {
            "name": leader["name"],
            "points": leader["points"],
            "alive": leader["alive"],
        },
        "projected": {
            "name": projected["name"],
            "dollars_alive": projected["dollars_alive"],
            "points": projected["points"],
            "alive": projected["alive"],
        },
    }
