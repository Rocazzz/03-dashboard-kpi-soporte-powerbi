"""
Genera los datos de tickets de una mesa de ayuda (Helpdesk) y los organiza en un
MODELO ESTRELLA listo para importar en Power BI:

  fact_tickets  ->  dim_fecha, dim_agente, dim_categoria, dim_canal

Además calcula los KPIs con pandas (para validar luego las medidas DAX) y
genera un prototipo visual del dashboard en `img/prototipo_dashboard.png`.

Uso:  python src/construir_modelo.py
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

rng = np.random.default_rng(2025)
BASE = Path(__file__).resolve().parents[1]
MODEL = BASE / "data" / "modelo_estrella"
MODEL.mkdir(parents=True, exist_ok=True)
(BASE / "img").mkdir(exist_ok=True)

# ---------------- Dimensiones ----------------
dim_agente = pd.DataFrame({
    "agente_id": range(1, 9),
    "agente": ["Laura P.", "Andrés M.", "Camila R.", "Jorge T.", "Natalia G.", "Esteban V.", "Paola D.", "Miguel A."],
    "nivel": ["N1", "N1", "N1", "N1", "N1", "N2", "N2", "N2"],
    "fecha_ingreso": pd.to_datetime(["2023-02-01", "2024-06-15", "2022-09-01", "2025-03-01",
                                     "2024-01-10", "2021-11-01", "2023-07-20", "2025-01-15"]),
})
dim_categoria = pd.DataFrame({
    "categoria_id": range(1, 8),
    "categoria": ["Acceso / contraseñas", "Sitio web caído", "Formularios web", "Correo corporativo",
                  "Hardware", "Software / licencias", "Integraciones (Sheets/CRM)"],
    "sla_horas": [4, 2, 8, 6, 24, 16, 12],
    "complejidad": [1, 3, 2, 2, 2, 2, 3],
})
dim_canal = pd.DataFrame({"canal_id": range(1, 5), "canal": ["Portal web", "Email", "WhatsApp", "Teléfono"]})

fechas = pd.date_range("2025-01-01", "2025-12-31", freq="D")
dim_fecha = pd.DataFrame({"fecha": fechas})
dim_fecha["fecha_id"] = dim_fecha.fecha.dt.strftime("%Y%m%d").astype(int)
dim_fecha["anio"] = dim_fecha.fecha.dt.year
dim_fecha["trimestre"] = "T" + dim_fecha.fecha.dt.quarter.astype(str)
dim_fecha["mes_num"] = dim_fecha.fecha.dt.month
dim_fecha["mes"] = dim_fecha.mes_num.map({1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun", 7: "Jul",
                                           8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"})
dim_fecha["dia_semana"] = dim_fecha.fecha.dt.dayofweek.map(dict(enumerate(["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"])))
dim_fecha["es_fin_de_semana"] = dim_fecha.fecha.dt.dayofweek >= 5
dim_fecha = dim_fecha[["fecha_id", "fecha", "anio", "trimestre", "mes_num", "mes", "dia_semana", "es_fin_de_semana"]]

# ---------------- Hechos ----------------
rows = []
tid = 1
for f in fechas:
    base = 22 if f.dayofweek < 5 else 6
    if f.month in (1, 7): base *= 1.25  # picos por renovaciones / temporada
    for _ in range(rng.poisson(base)):
        cat = rng.choice(dim_categoria.categoria_id, p=[.24, .07, .16, .15, .12, .14, .12])
        sla = dim_categoria.loc[dim_categoria.categoria_id == cat, "sla_horas"].iloc[0]
        comp = dim_categoria.loc[dim_categoria.categoria_id == cat, "complejidad"].iloc[0]
        escalado = rng.random() < 0.08 * comp
        agente = rng.choice([6, 7, 8]) if escalado else rng.choice([1, 2, 3, 4, 5], p=[.25, .2, .25, .1, .2])
        experiencia = 1.25 if agente in (4, 8) else 1.0  # agentes nuevos tardan un poco más
        presion = {1: .42, 2: .78, 3: .50, 4: .48, 5: .40, 6: .52, 7: .70}[int(cat)]  # holgura real vs SLA
        horas = rng.lognormal(np.log(sla * presion), 0.6) * experiencia * (1.3 if escalado else 1)
        canal = int(rng.choice(dim_canal.canal_id, p=[.4, .25, .25, .1]))
        factor_canal = {1: 1.0, 2: 2.2, 3: 0.45, 4: 0.3}[canal]  # email es el canal más lento
        primera_resp_min = rng.lognormal(np.log((25 if f.dayofweek < 5 else 70) * factor_canal), 0.7)
        resuelto_1er_contacto = (not escalado) and rng.random() < (0.72 - 0.15 * comp)
        estado = "Abierto" if (f > pd.Timestamp("2025-12-27") and rng.random() < .5) else "Cerrado"
        csat = None
        if estado == "Cerrado" and rng.random() < 0.45:
            p_buena = 0.9 if horas <= sla else 0.55
            csat = int(rng.choice([5, 4], p=[.6, .4])) if rng.random() < p_buena else int(rng.choice([1, 2, 3], p=[.2, .3, .5]))
        apertura = f + pd.Timedelta(minutes=int(rng.integers(7 * 60, 19 * 60)))
        rows.append({
            "ticket_id": tid, "fecha_id": int(f.strftime("%Y%m%d")), "fecha_apertura": apertura,
            "fecha_cierre": apertura + pd.Timedelta(hours=float(horas)) if estado == "Cerrado" else pd.NaT,
            "agente_id": int(agente), "categoria_id": int(cat),
            "canal_id": canal,
            "prioridad": rng.choice(["Baja", "Media", "Alta", "Crítica"], p=[.3, .45, .2, .05]),
            "estado": estado, "escalado": bool(escalado),
            "minutos_primera_respuesta": round(float(primera_resp_min), 1),
            "horas_resolucion": round(float(horas), 2) if estado == "Cerrado" else None,
            "cumple_sla": bool(horas <= sla) if estado == "Cerrado" else None,
            "resuelto_primer_contacto": bool(resuelto_1er_contacto),
            "csat": csat,
        })
        tid += 1
fact = pd.DataFrame(rows)

for nombre, df in {"fact_tickets": fact, "dim_fecha": dim_fecha, "dim_agente": dim_agente,
                   "dim_categoria": dim_categoria, "dim_canal": dim_canal}.items():
    df.to_csv(MODEL / f"{nombre}.csv", index=False, encoding="utf-8")

# ---------------- KPIs de referencia (para validar las medidas DAX) ----------------
cerr = fact[fact.estado == "Cerrado"]
kpis = {
    "Total tickets": len(fact),
    "% Cumplimiento SLA": f"{cerr.cumple_sla.mean():.1%}",
    "Tiempo medio de resolución (h)": round(cerr.horas_resolucion.mean(), 1),
    "Mediana primera respuesta (min)": round(fact.minutos_primera_respuesta.median(), 1),
    "% Resolución en primer contacto (FCR)": f"{fact.resuelto_primer_contacto.mean():.1%}",
    "% Escalados a N2": f"{fact.escalado.mean():.1%}",
    "CSAT (% 4-5)": f"{(cerr.csat.dropna() >= 4).mean():.1%}",
    "Backlog (abiertos)": int((fact.estado == "Abierto").sum()),
}
pd.Series(kpis).to_frame("valor").to_csv(BASE / "data" / "kpis_referencia.csv")
print("KPIs de referencia:")
for k, v in kpis.items():
    print(f"  {k:40s} {v}")

# ---------------- Prototipo visual del dashboard ----------------
AZUL, GRIS, NARANJA, VERDE, ROJO = "#2a6f97", "#c9d1d9", "#e07a2f", "#2e8b57", "#c0392b"
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "font.size": 9})
fig = plt.figure(figsize=(15, 8.5), facecolor="white")
gs = fig.add_gridspec(3, 4, height_ratios=[0.55, 1.4, 1.4], hspace=0.55, wspace=0.35)
fig.suptitle("Dashboard de KPIs · Mesa de Ayuda 2025 (prototipo)", x=0.06, ha="left", fontsize=16, fontweight="bold")

tarjetas = [("Tickets", f"{len(fact):,}", AZUL), ("Cumplimiento SLA", kpis["% Cumplimiento SLA"], VERDE),
            ("FCR", kpis["% Resolución en primer contacto (FCR)"], AZUL), ("CSAT", kpis["CSAT (% 4-5)"], NARANJA)]
for i, (t, v, c) in enumerate(tarjetas):
    ax = fig.add_subplot(gs[0, i]); ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, color="#f4f6f8", transform=ax.transAxes))
    ax.text(0.06, 0.62, t, fontsize=11, color="#555", transform=ax.transAxes)
    ax.text(0.06, 0.12, v, fontsize=22, fontweight="bold", color=c, transform=ax.transAxes)

m = fact.merge(dim_fecha[["fecha_id", "mes_num", "mes"]], on="fecha_id")
mens = m.groupby(["mes_num", "mes"]).agg(tickets=("ticket_id", "size"), sla=("cumple_sla", "mean")).reset_index()
fila1 = gs[1, :].subgridspec(1, 2, wspace=0.55)
ax = fig.add_subplot(fila1[0])
ax.bar(mens.mes, mens.tickets, color=GRIS)
ax2 = ax.twinx(); ax2.plot(mens.mes, mens.sla * 100, color=AZUL, marker="o", lw=2); ax2.set_ylim(50, 100); ax2.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax2.axhline(85, color=ROJO, ls="--", lw=1); ax2.text(-0.4, 86.5, "Meta 85%", color=ROJO, ha="left")
ax2.spines["top"].set_visible(False)
ax.set_title("Volumen mensual de tickets y % SLA", loc="left", fontweight="bold")

cat = cerr.merge(dim_categoria, on="categoria_id").groupby("categoria").cumple_sla.mean().sort_values()
ax = fig.add_subplot(fila1[1])
ax.barh(cat.index, cat.values * 100, color=[ROJO if v < .85 else VERDE for v in cat.values])
ax.axvline(85, color="#555", ls="--", lw=1); ax.set_xlim(50, 100)
ax.set_title("% Cumplimiento SLA por categoría", loc="left", fontweight="bold")

ag = cerr.merge(dim_agente, on="agente_id").groupby("agente").agg(t=("ticket_id", "size"), h=("horas_resolucion", "mean")).sort_values("t")
ax = fig.add_subplot(gs[2, :2])
ax.barh(ag.index, ag.t, color=AZUL)
for i, (t, h) in enumerate(zip(ag.t, ag.h)): ax.text(t + 10, i, f"{h:.1f} h prom.", va="center", fontsize=8, color="#555")
ax.set_title("Tickets cerrados por agente (y horas promedio)", loc="left", fontweight="bold")

can = fact.merge(dim_canal, on="canal_id").groupby("canal").minutos_primera_respuesta.median().sort_values()
ax = fig.add_subplot(gs[2, 2])
ax.bar(can.index, can.values, color=NARANJA); ax.tick_params(axis="x", rotation=20)
ax.set_title("Mediana 1ª respuesta (min)", loc="left", fontweight="bold")

dia = m.assign(d=pd.to_datetime(m.fecha_apertura).dt.dayofweek).groupby("d").size()
ax = fig.add_subplot(gs[2, 3])
ax.bar(["L", "M", "X", "J", "V", "S", "D"], dia.values, color=GRIS)
ax.set_title("Tickets por día de la semana", loc="left", fontweight="bold")

fig.savefig(BASE / "img" / "prototipo_dashboard.png", dpi=110, bbox_inches="tight")
print("Prototipo guardado en img/prototipo_dashboard.png")
