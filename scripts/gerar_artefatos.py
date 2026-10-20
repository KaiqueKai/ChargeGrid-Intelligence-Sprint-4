"""Regenera resultados de referência e diagramas do repositório."""
from __future__ import annotations
import csv
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

from dashboard import gerar_dashboard_sprint4
from energy_manager import EVRequest, SystemConfig, recommend_mode


def main():
    vehicles = [EVRequest(f"EV{i}", 7.0, 7.0, 1.0) for i in range(1, 4)]
    config = SystemConfig(hour=12, duration_h=1, pv_peak_kw=15, weather_factor=.85,
                          station_limit_kw=22, grid_limit_kw=15, battery_soc_initial_pct=50,
                          battery_soc_min_pct=20)
    mode, comparisons = recommend_mode(vehicles, config)
    result = next(row for row in comparisons if row["modo"] == mode)
    payload = {
        "projeto": "ChargeGrid Intelligence — Sprint 4",
        "tipo_dado": "simulacao_deterministica",
        "configuracao": {
            "hora": config.hour, "duracao_h": config.duration_h, "pv_peak_kw": config.pv_peak_kw,
            "fator_clima": config.weather_factor, "limite_estacao_kw": config.station_limit_kw,
            "limite_rede_kw": config.grid_limit_kw, "capacidade_bateria_kwh": config.battery_capacity_kwh,
            "soc_inicial_pct": config.battery_soc_initial_pct, "soc_minimo_pct": config.battery_soc_min_pct,
            "veiculos": [{"id": v.vehicle_id, "potencia_maxima_kw": v.max_power_kw,
                          "energia_solicitada_kwh": v.requested_energy_kwh, "prioridade": v.priority}
                         for v in vehicles],
        },
        "modo_recomendado": mode,
        "resultado": result,
        "comparacao_modos": comparisons,
    }
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "cenario_referencia.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = ["modo", "energia_entregue_kwh", "energia_nao_atendida_kwh", "solar_usada_kwh",
              "bateria_fornecida_kwh", "rede_importada_kwh", "custo_total_rs", "economia_estimada_rs",
              "emissoes_estimadas_kg_co2e", "emissoes_evitas_estimadas_kg_co2e", "battery_soc_after_pct"]
    with (reports / "comparacao_modos.csv").open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in comparisons:
            writer.writerow({field: row[field] for field in fields})
    gerar_dashboard_sprint4(result, reports / "dashboard_sprint4_exemplo.png")
    _draw_architecture(ROOT / "docs" / "arquitetura_sprint4.png")
    print(f"Artefatos regenerados. Modo recomendado: {mode}")


def _draw_architecture(output: Path):
    fig, ax = plt.subplots(figsize=(16, 9), dpi=160)
    ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.axis("off")
    fig.patch.set_facecolor("#f7f9fc"); ax.set_facecolor("#f7f9fc")
    ax.text(8, 8.55, "CHARGEGRID INTELLIGENCE — SPRINT 4", ha="center", va="center", fontsize=20,
            fontweight="bold", color="#152c45")
    ax.text(8, 8.12, "Arquitetura funcional da simulação integrada", ha="center", va="center", fontsize=12, color="#526579")
    boxes = {
        "input": (0.5, 5.9, 3.0, 1.35, "ENTRADAS DO CENÁRIO", "Hora • clima • EVs\nSOC • limites • duração", "#e4edff", "#2f5597"),
        "solar": (4.2, 6.15, 3.0, 1.2, "GERAÇÃO SOLAR", "solar_module.py\ncurva determinística", "#fff1cc", "#b57918"),
        "battery": (4.2, 4.45, 3.0, 1.2, "ARMAZENAMENTO", "battery_module.py\nSOC • eficiência • reserva", "#dcf4e6", "#2b8057"),
        "control": (8.0, 5.25, 3.4, 1.6, "CONTROLADOR ENERGÉTICO", "energy_manager.py\nlimites • rateio ponderado\ncomparador de estratégias", "#d6f0e1", "#237348"),
        "tariff": (12.3, 6.15, 3.0, 1.2, "TARIFAÇÃO MISTA", "tarifa_module.py\ncusto solar / bateria / rede", "#ffeadc", "#bd642a"),
        "vehicles": (12.3, 4.45, 3.0, 1.2, "VEÍCULOS ELÉTRICOS", "potência por veículo\nenergia entregue / pendente", "#e4edff", "#2f5597"),
        "dashboard": (5.2, 2.25, 5.6, 1.25, "DASHBOARD + RESULTADOS", "dashboard + assistente local explicável\ngráficos • exportação JSON / CSV / PNG", "#e5e9f4", "#536b99"),
        "goodwe": (0.5, 2.15, 3.5, 1.5, "REFERÊNCIA GOODWE HCA G2", "Modos PV Priority / PV + BAT / Fast\nequilíbrio dinâmico de carga", "#fff1cc", "#b57918"),
        "boundary": (11.6, 2.15, 3.7, 1.5, "LIMITE DECLARADO", "Simulação acadêmica\nsem conexão física ou telemetria", "#ffe3e3", "#b43f3f"),
    }
    centers = {}
    for key, (x, y, w, h, title, body, face, edge) in boxes.items():
        patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06,rounding_size=0.12",
                               linewidth=1.7, edgecolor=edge, facecolor=face)
        ax.add_patch(patch)
        centers[key] = (x + w / 2, y + h / 2)
        ax.text(x + w / 2, y + h * .69, title, ha="center", va="center", fontsize=10.5,
                fontweight="bold", color="#18314a")
        ax.text(x + w / 2, y + h * .36, body, ha="center", va="center", fontsize=9.2,
                color="#2c3e50", linespacing=1.35)
    def arrow(a, b, start_offset=(0, 0), end_offset=(0, 0), color="#66788a", lw=1.8, rad=0):
        p1 = (centers[a][0] + start_offset[0], centers[a][1] + start_offset[1])
        p2 = (centers[b][0] + end_offset[0], centers[b][1] + end_offset[1])
        ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=14, linewidth=lw,
                                     color=color, connectionstyle=f"arc3,rad={rad}"))
    arrow("input", "solar", (1.5, .35), (-1.5, -.2))
    arrow("input", "control", (1.5, -.2), (-1.7, .5))
    arrow("solar", "control", (1.5, -.2), (-1.7, .25))
    arrow("battery", "control", (1.5, .1), (-1.7, -.25))
    arrow("control", "tariff", (1.7, .45), (-1.5, -.15))
    arrow("control", "vehicles", (1.7, -.35), (-1.5, .15))
    arrow("tariff", "dashboard", (-1.2, -.55), (2.1, .5), rad=-.08)
    arrow("vehicles", "dashboard", (-1.2, -.5), (2.1, .05), rad=.08)
    arrow("goodwe", "control", (1.7, .6), (-1.6, -.7), color="#a97821", lw=1.5, rad=-.05)
    arrow("dashboard", "boundary", (2.8, 0), (-1.85, 0), color="#ad6262", lw=1.5)
    ax.text(8, 1.2, "Premissas transparentes • testes automatizados • resultados reproduzíveis",
            ha="center", va="center", fontsize=11, color="#526579")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == "__main__":
    main()
