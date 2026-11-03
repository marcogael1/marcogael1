"""
Genera assets/commits-por-mes.svg con los commits de los últimos 12 meses.

Usa la API GraphQL de GitHub (contributionsCollection). Con un token personal
del dueño del perfil incluye las contribuciones privadas (repos de Freepi-Inc).

Variables de entorno:
  GH_TOKEN     token personal (scope: read:user, repo)
  GH_USER      usuario de GitHub (default: marcogael1)
  OUTPUT       ruta del SVG (default: assets/commits-por-mes.svg)
  MONTHS       meses a mostrar (default: 12)
"""
import json
import os
import urllib.request
from datetime import date, datetime, timedelta, timezone

TOKEN = os.environ.get("GH_TOKEN", "")
USER = os.environ.get("GH_USER", "marcogael1")
OUTPUT = os.environ.get("OUTPUT", "assets/commits-por-mes.svg")
MONTHS = int(os.environ.get("MONTHS", "12"))
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

# Colores tokyonight (igual que las demás tarjetas del README)
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
    """Lista de (inicio, fin) de los últimos n meses, incluido el actual."""
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
        # restrictedContributionsCount = contribuciones privadas (sin detalle por tipo)
        datos.append((inicio, c["totalCommitContributions"] + c["restrictedContributionsCount"]))
    return datos


def svg(datos):
    W, H = 840, 345
    left, right, top, bottom = 50, 20, 115, 50
    cw, ch = W - left - right, H - top - bottom
    maximo = max((v for _, v in datos), default=0) or 1
    # Escala con pasos redondos (1, 2, 5 × 10^n)
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
        f'<text x="25" y="35" fill="{TITLE}" font-size="18" font-weight="600">Commits por mes</text>',
        f'<text x="{W - 25}" y="35" fill="{MUTED}" font-size="12" text-anchor="end">últimos {len(datos)} meses</text>',
    ]

    # Resumen
    resumen = [
        ("Total", f"{total:,}"),
        (f"En {anio}", f"{este_anio:,}"),
        ("Promedio / mes", f"{promedio:,}"),
        ("Mejor mes", f"{MESES[mejor[0].month - 1]} {mejor[0].year} · {mejor[1]:,}"),
    ]
    x = 25
    for etiqueta, valor in resumen:
        out.append(f'<text x="{x}" y="62" fill="{MUTED}" font-size="11">{etiqueta}</text>')
        out.append(f'<text x="{x}" y="80" fill="{TEXT}" font-size="15" font-weight="600">{valor}</text>')
        x += 140 if etiqueta != "Promedio / mes" else 150

    # Grid
    for i in range(5):
        val = round(tope * i / 4)
        y = top + ch - ch * i / 4
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{W - right}" y2="{y:.1f}" stroke="{GRID}"/>')
        out.append(f'<text x="{left - 8}" y="{y + 4:.1f}" fill="{MUTED}" font-size="10" text-anchor="end">{val}</text>')

    # Barras
    slot = cw / len(datos)
    bw = min(40, slot * 0.6)
    for i, (d, v) in enumerate(datos):
        h = ch * v / tope
        bx = left + slot * i + (slot - bw) / 2
        by = top + ch - h
        color = BAR_CUR if i == len(datos) - 1 else BAR
        out.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{max(h, 0):.1f}" rx="3" fill="{color}">'
                   f'<title>{MESES[d.month - 1]} {d.year}: {v} commits</title></rect>')
        if v:
            out.append(f'<text x="{bx + bw / 2:.1f}" y="{by - 5:.1f}" fill="{TEXT}" font-size="10" text-anchor="middle">{v}</text>')
        etiqueta = MESES[d.month - 1] + (f" {str(d.year)[2:]}" if d.month == 1 or i == 0 else "")
        out.append(f'<text x="{bx + bw / 2:.1f}" y="{top + ch + 18}" fill="{MUTED}" font-size="11" text-anchor="middle">{etiqueta}</text>')

    act = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    out.append(f'<text x="{W - 25}" y="{H - 12}" fill="{MUTED}" font-size="10" text-anchor="end">Actualizado {act}</text>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    if os.environ.get("DEMO"):
        import random
        datos = [(ini, random.randint(20, 160)) for ini, _ in meses_atras(MONTHS)]
    else:
        if not TOKEN:
            raise SystemExit("Falta GH_TOKEN")
        datos = obtener_datos()
    os.makedirs(os.path.dirname(OUTPUT) or ".", exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(svg(datos))
    print(f"OK -> {OUTPUT}: {sum(v for _, v in datos)} commits en {len(datos)} meses")
