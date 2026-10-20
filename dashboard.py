"""Gráfico estático da sessão para documentação e relatório."""
from __future__ import annotations
from pathlib import Path


def gerar_grafico(dados_veiculos, caminho="dashboard_sessao.png"):
    """Compatibilidade com o gráfico original da Sprint 3."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    veiculos = [f"Veículo {d['id']}" for d in dados_veiculos]
    consumo = [float(d["consumo"]) for d in dados_veiculos]
    valores = [float(d["valor"]) for d in dados_veiculos]
    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax1.bar(veiculos, consumo, label="Consumo (kWh)")
    ax1.set_ylabel("Consumo (kWh)")
    ax1.set_xlabel("Veículo")
    ax1.set_title("ChargeGrid Intelligence — sessão de recarga")
    ax1.tick_params(axis="x", rotation=15)
    ax2 = ax1.twinx()
    ax2.plot(veiculos, valores, marker="o", linewidth=2, label="Custo (R$)")
    ax2.set_ylabel("Custo (R$)")
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left")
    fig.tight_layout()
    fig.savefig(caminho, dpi=160)
    plt.close(fig)
    return Path(caminho)


def gerar_dashboard_sprint4(resultado: dict, caminho="reports/dashboard_sprint4_exemplo.png"):
    """Gera um gráfico com fontes energéticas e atendimento/custo por EV."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    output = Path(caminho)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.3))

    sources = ["Solar direta", "Bateria", "Rede"]
    source_values = [resultado["solar_usada_kwh"], resultado["bateria_fornecida_kwh"], resultado["rede_importada_kwh"]]
    bars = ax1.bar(sources, source_values)
    ax1.set_title("Energia entregue por fonte")
    ax1.set_ylabel("Energia (kWh)")
    ax1.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, source_values):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f"{value:.2f}", ha="center", va="bottom", fontsize=9)

    vehicles = resultado["veiculos"]
    labels = [str(v['veiculo']) if str(v['veiculo']).upper().startswith("EV") else f"EV {v['veiculo']}" for v in vehicles]
    delivered = [v["energia_entregue_kwh"] for v in vehicles]
    costs = [v["custo_rs"] for v in vehicles]
    x = list(range(len(labels)))
    bars2 = ax2.bar(x, delivered, label="Energia entregue (kWh)")
    ax2.set_xticks(x, labels)
    ax2.set_ylabel("Energia entregue (kWh)")
    ax2.set_ylim(0, max(delivered or [1]) * 1.28)
    ax2.set_title("Atendimento por veículo")
    ax2.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax2.grid(axis="y", alpha=0.25)
    for bar, value, cost in zip(bars2, delivered, costs):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f"{value:.2f} kWh\nR$ {cost:.2f}", ha="center", va="bottom", fontsize=8)
    fig.suptitle(f"ChargeGrid Intelligence | {resultado['modo']} | SIMULAÇÃO", fontsize=14, fontweight="bold")
    fig.text(0.5, 0.01, "Valores didáticos; sem conexão física ou telemetria GoodWe.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    fig.savefig(output, dpi=170, bbox_inches="tight")
    plt.close(fig)
    return output
