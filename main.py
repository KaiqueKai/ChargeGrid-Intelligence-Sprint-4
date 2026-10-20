"""CLI da Sprint 4 — execução guiada, com valores padrão e validação de entradas."""
from __future__ import annotations
import json
from pathlib import Path

from ai_module import MODOS_CARREGAMENTO
from dashboard import gerar_dashboard_sprint4
from energy_manager import EVRequest, SystemConfig, compare_modes, recommend_mode, simulate_session

ROOT = Path(__file__).resolve().parent


def _ask_number(prompt: str, default: float, min_value: float, max_value: float | None = None) -> float:
    while True:
        raw = input(f"{prompt} [{default}]: ").strip()
        try:
            value = default if not raw else float(raw.replace(",", "."))
        except ValueError:
            print("Digite um número válido ou pressione Enter para usar o padrão.")
            continue
        if value < min_value or (max_value is not None and value > max_value):
            bound = f"entre {min_value} e {max_value}" if max_value is not None else f"maior ou igual a {min_value}"
            print(f"O valor precisa ser {bound}.")
            continue
        return value


def main() -> None:
    print("=" * 72)
    print("CHARGEGRID INTELLIGENCE — SPRINT 4 | SIMULADOR INTEGRADO")
    print("Projeto acadêmico: todos os dados são simulados; sem ligação física GoodWe.")
    print("Unidades: potência kW | energia kWh | duração h")
    print("=" * 72)

    vehicle_count = int(_ask_number("Quantidade de veículos", 3, 1, 12))
    hour = _ask_number("Hora da simulação (0–24)", 12, 0, 24)
    soc = _ask_number("Carga inicial da bateria (%)", 50, 20, 100)
    station_limit = _ask_number("Limite total da estação (kW)", 22, 1, 250)
    grid_limit = _ask_number("Limite de potência importada da rede (kW)", 15, 0, 250)
    duration = _ask_number("Duração do intervalo simulado (horas)", 1, 0.25, 24)
    weather = _ask_number("Fator climático solar (0 a 1; 0,85 = 85%)", 0.85, 0, 1)

    vehicles: list[EVRequest] = []
    print("\nConfigure cada veículo. Para a demonstração de 1 hora, 7 kWh e 7 kW são valores coerentes.")
    for i in range(1, vehicle_count + 1):
        power = _ask_number(f"Veículo {i} — potência máxima (kW)", 7, 0.1, 22)
        energy = _ask_number(f"Veículo {i} — energia solicitada na sessão (kWh)", 7, 0.1, 250)
        priority = _ask_number(f"Veículo {i} — prioridade (1 = padrão)", 1, 0.1, 5)
        vehicles.append(EVRequest(str(i), power, energy, priority))

    print("\nModo de carregamento:")
    print("  AUTO — comparar modos e recomendar o melhor para este cenário")
    for index, option in enumerate(MODOS_CARREGAMENTO, start=1):
        print(f"  {index} — {option}")
    raw_mode = input("Escolha [AUTO]: ").strip().upper()
    if raw_mode in ("", "AUTO", "A"):
        config = SystemConfig(
            hour=hour, duration_h=duration, battery_soc_initial_pct=soc,
            station_limit_kw=station_limit, grid_limit_kw=grid_limit,
            weather_factor=weather,
        )
        recommended, comparisons = recommend_mode(vehicles, config)
        result = next(item for item in comparisons if item["modo"] == recommended)
        print(f"\nRecomendação do algoritmo: {recommended}")
        print("Critério: minimizar energia não atendida; depois custo; depois emissões estimadas.")
    else:
        try:
            index = int(raw_mode) - 1
            mode = MODOS_CARREGAMENTO[index]
        except (ValueError, IndexError):
            print("Modo inválido. A execução será feita com AUTO.")
            mode = None
        config = SystemConfig(
            hour=hour, duration_h=duration, battery_soc_initial_pct=soc,
            station_limit_kw=station_limit, grid_limit_kw=grid_limit,
            weather_factor=weather,
        )
        if mode is None:
            recommended, comparisons = recommend_mode(vehicles, config)
            result = next(item for item in comparisons if item["modo"] == recommended)
        else:
            result = simulate_session(vehicles, config, mode)
            comparisons = compare_modes(vehicles, config)

    print("\n" + "=" * 72)
    print("RESULTADO DA SESSÃO")
    print("=" * 72)
    print(f"Modo aplicado: {result['modo']}")
    print(f"Geração solar: {result['geracao_solar_kw']:.2f} kW")
    print(f"Demanda solicitada: {result['demanda_solicitada_kw']:.2f} kW")
    print(f"Potência atendida: {result['potencia_atendida_kw']:.2f} kW")
    print(f"Energia entregue no intervalo: {result['energia_entregue_kwh']:.2f} kWh")
    print(f"Fontes para os veículos — solar / bateria / rede: "
          f"{result['solar_usada_kwh']:.2f} / {result['bateria_fornecida_kwh']:.2f} / {result['rede_importada_kwh']:.2f} kWh")
    print(f"Bateria: {result['battery_soc_before_pct']:.1f}% -> {result['battery_soc_after_pct']:.1f}%")
    if result['bateria_carregada_kwh'] > 0:
        print(f"Energia armazenada do excedente solar: {result['bateria_carregada_kwh']:.2f} kWh")
    print(f"Custo demonstrativo: R$ {result['custo_total_rs']:.2f}")
    print(f"Referência se toda energia entregue viesse da rede: R$ {result['custo_referencia_toda_rede_rs']:.2f}")
    print(f"Economia estimada: R$ {result['economia_estimada_rs']:.2f}")
    print(f"Participação solar direta: {result['participacao_solar_direta_pct']:.1f}%")
    print(f"Emissões estimadas: {result['emissoes_estimadas_kg_co2e']:.3f} kg CO2e")
    print(f"Emissões evitadas estimadas vs. referência: {result['emissoes_evitas_estimadas_kg_co2e']:.3f} kg CO2e")

    print("\nDistribuição por veículo:")
    print(f"{'Veículo':<12}{'Potência kW':>13}{'Energia kWh':>14}{'Custo R$':>12}{'Pendente kWh':>15}")
    for row in result["veiculos"]:
        print(f"{row['veiculo']:<12}{row['potencia_atendida_kw']:>13.2f}{row['energia_entregue_kwh']:>14.2f}"
              f"{row['custo_rs']:>12.2f}{row['energia_nao_atendida_kwh']:>15.2f}")

    print("\nAlertas e decisões:")
    for alert in result["alertas"]:
        print(f"- {alert}")
    print("\nComparação de modos (mesmas entradas e estado inicial):")
    for row in comparisons:
        print(f"- {row['modo']}: entregue={row['energia_entregue_kwh']:.2f} kWh; "
              f"pendente={row['energia_nao_atendida_kwh']:.2f} kWh; custo=R$ {row['custo_total_rs']:.2f}; "
              f"CO2e={row['emissoes_estimadas_kg_co2e']:.3f} kg")

    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    json_path = reports_dir / "ultima_simulacao.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    image_path = reports_dir / "dashboard_sprint4_exemplo.png"
    try:
        gerar_dashboard_sprint4(result, image_path)
        print(f"\nGráfico salvo em: {image_path.relative_to(ROOT)}")
    except ImportError:
        print("\nMatplotlib não encontrado; instale as dependências para gerar o gráfico.")
    print(f"Resultado estruturado salvo em: {json_path.relative_to(ROOT)}")
    print("\nObservação: tarifas e fatores de emissão são didáticos, não dados oficiais nem medição real.")


if __name__ == "__main__":
    main()
