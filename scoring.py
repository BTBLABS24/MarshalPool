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

        for pick in p.picks:
            state = team_states.get(pick.team)
            if state is None:
                # Team hasn't appeared in any game yet - still alive
                alive += 1
                pts = 0
                mx = MAX_POINTS
            elif state.status == "eliminated":
                eliminated += 1
                pts = state.points_earned
                mx = 0
            else:
                alive += 1
                pts = state.points_earned
                mx = state.max_remaining

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

    # Current leader: highest points
    leader = entries[0]

    # Projected leader: highest max_possible (who could end up with most points)
    projected = max(entries, key=lambda e: e["max_possible"])

    # Longshot: person with fewest alive teams but still has a viable max_possible
    # among those in the top half of max_possible
    alive_entries = [e for e in entries if e["alive"] > 0]
    if alive_entries:
        median_max = sorted(
            [e["max_possible"] for e in alive_entries]
        )[len(alive_entries) // 2]
        viable = [e for e in alive_entries if e["max_possible"] >= median_max]
        if viable:
            longshot = min(viable, key=lambda e: e["alive"])
        else:
            longshot = min(alive_entries, key=lambda e: e["alive"])
    else:
        longshot = entries[-1]

    return {
        "leader": {
            "name": leader["name"],
            "points": leader["points"],
            "alive": leader["alive"],
        },
        "projected": {
            "name": projected["name"],
            "max_possible": projected["max_possible"],
            "points": projected["points"],
            "alive": projected["alive"],
        },
        "longshot": {
            "name": longshot["name"],
            "points": longshot["points"],
            "alive": longshot["alive"],
            "max_possible": longshot["max_possible"],
            "num_teams": longshot["num_teams"],
        },
    }
