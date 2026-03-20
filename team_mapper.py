"""Maps Excel team names to ESPN API canonical names (team.location field)."""

EXCEL_TO_ESPN = {
    "Brigham Young": "BYU",
    "Cal Baptist": "California Baptist",
    "Central Florida": "UCF",
    "Connecticut": "UConn",
    "Hawaii": "Hawai'i",
    "Long Island": "Long Island University",
    "McNeese State": "McNeese",
    "Miami (FL)": "Miami",
    "Queens": "Queens University",
    "St. Mary's": "Saint Mary's",
    "Texas Christian": "TCU",
    "Virginia Commonwealth": "VCU",
    "Viriginia Commonwealth": "VCU",  # typo in Excel (Joe Jansen)
    "Virgina": "Virginia",  # typo in Excel (Jon Petoskey)
}


def normalize(team_name: str) -> str:
    name = team_name.strip()
    return EXCEL_TO_ESPN.get(name, name)
