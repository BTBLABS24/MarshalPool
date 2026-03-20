"""Loads participant rosters from the Excel file."""

import openpyxl
from dataclasses import dataclass, field
from team_mapper import normalize


@dataclass
class TeamPick:
    team: str  # ESPN-normalized name
    seed: int
    cost: int


@dataclass
class Participant:
    first: str
    last: str
    name: str  # "First Last" display key
    picks: list[TeamPick] = field(default_factory=list)
    total_cost: int = 0


def load_rosters(path: str) -> dict[str, Participant]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["Rosters"]

    participants: dict[str, Participant] = {}

    for row in ws.iter_rows(min_row=2, values_only=True):
        first_raw, last_raw, seed, team_raw, cost = row
        if not first_raw or not last_raw:
            continue

        first = str(first_raw).strip()
        last = str(last_raw).strip()
        name = f"{first} {last}"
        team = normalize(str(team_raw))
        seed = int(seed)
        cost = int(cost)

        if name not in participants:
            participants[name] = Participant(first=first, last=last, name=name)

        p = participants[name]
        p.picks.append(TeamPick(team=team, seed=seed, cost=cost))
        p.total_cost += cost

    wb.close()
    return participants
