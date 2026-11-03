"""
Generates assets/commits-por-mes.svg with the commits of the last 12 months.

Uses the GitHub GraphQL API (contributionsCollection), including private
contributions when they are enabled on the profile.

Environment variables:
  GH_TOKEN     personal token (scope: read:user)
  GH_USER      GitHub username (default: marcogael1)
  OUTPUT       SVG path (default: assets/commits-por-mes.svg)
  MONTHS       months to show (default: 12)
"""
import json
import os
import urllib.request
from datetime import date, datetime, timedelta, timezone

TOKEN = os.environ.get("GH_TOKEN", "")
USER = os.environ.get("GH_USER", "marcogael1")
OUTPUT = os.environ.get("OUTPUT", "assets/commits-por-mes.svg")
MONTHS = int(os.environ.get("MONTHS", "12"))
MESES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Tokyonight colors (same as the other README cards)
BG, TITLE, TEXT, MUTED, BAR, BAR_CUR, GRID = (
    "#1a1b27", "#70a5fd", "#a9b1d6", "#565f89", "#38bdae", "#bf91f3", "#24283b"
)

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      restrictedContributionsCount
    }
  }
}
"""


def gql(variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]["user"]["contributionsCollection"]


def meses_atras(n):
    """List of (start, end) for the last n months, including the current one."""
    hoy = date.today()
    y, m = hoy.year, hoy.month
    rangos = []
    for _ in range(n):
        inicio = date(y, m, 1)
        sig = date(y + (m == 12), m % 12 + 1, 1)
        fin = min(sig - timedelta(days=1), hoy)
        rangos.append((inicio, fin))
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return list(reversed(rangos))


def obtener_datos():
    datos = []
    for inicio, fin in meses_atras(MONTHS):
        c = gql({
            "login": USER,
            "from": f"{inicio}T00:00:00Z",
            "to": f"{fin}T23:59:59Z",
        })
        # restrictedContributionsCount = private contributions (no breakdown by type)
        datos.append((inicio, c["totalCommitContributions"] + c["restrictedContributionsCount"]))
    return datos


def svg(datos):
    W, H = 840, 345
    left, right, top, bottom = 50, 20, 115, 50
    cw, ch = W - left - right, H - top - bottom
    maximo = max((v for _, v in datos), default=0) or 1
    # Axis scale with round steps (1, 2, 5 x 10^n)
    crudo = maximo / 4
    base = 10 ** max(0, len(str(int(crudo))) - 1)
    paso = next(m * base for m in (1, 2, 2.5, 5, 10) if m * base >= crudo)
    paso = max(1, int(paso))
    tope = paso * 4 if paso * 4 >= maximo else paso * 5

    total = sum(v for _, v in datos)
    mejor = max(datos, key=lambda d: d[1])
    promedio = round(total / len(datos)) if datos else 0
    anio = date.today().year
    este_anio = sum(v for d, v in datos if d.year == anio)

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="Segoe UI, Ubuntu, sans-serif">',
        f'<rect width="{W}" height="{H}" rx="6" fill="{BG}"/>',
        f'<text x="25" y="35" fill="{TITLE}" font-size="18" font-weight="600">Monthly commits</text>',
        f'<text x="{W - 25}" y="35" fill="{MUTED}" font-size="12" text-anchor="end">last {len(datos)} months</text>',
    ]

    # Summary
    resumen = [
        ("Total", f"{total:,}"),
        (f"In {anio}", f"{este_anio:,}"),
        ("Avg / month", f"{promedio:,}"),
        ("Best month", f"{MESES[mejor[0].month - 1]} {mejor[0].year} - {mejor[1]:,}"),
