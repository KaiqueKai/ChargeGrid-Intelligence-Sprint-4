"""Núcleo integrado da Sprint 4: despacho energético, limites e tarifação.

Unidades: potência em kW, energia em kWh, duração em horas, custo em R$.
É um simulador acadêmico determinístico; não lê nem comanda hardware GoodWe.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Iterable

from ai_module import MODOS_CARREGAMENTO, recomendar_modo
from battery_module import Bateria
from solar_module import gerar_energia_solar
from tarifa_module import calcular_custo_misto


@dataclass(frozen=True)
class EVRequest:
    vehicle_id: str
    max_power_kw: float = 7.0
    requested_energy_kwh: float = 12.0
    priority: float = 1.0

    def __post_init__(self):
        if not str(self.vehicle_id).strip():
            raise ValueError("Cada veículo precisa de um identificador.")
        if not math.isfinite(self.max_power_kw) or self.max_power_kw <= 0:
            raise ValueError("A potência máxima de cada veículo deve ser positiva.")
        if not math.isfinite(self.requested_energy_kwh) or self.requested_energy_kwh <= 0:
            raise ValueError("A energia solicitada por veículo deve ser positiva.")
        if not math.isfinite(self.priority) or self.priority <= 0:
            raise ValueError("A prioridade deve ser maior que zero.")


@dataclass(frozen=True)
class SystemConfig:
    hour: float = 12.0
    duration_h: float = 1.0
    pv_peak_kw: float = 15.0
    weather_factor: float = 0.85
    station_limit_kw: float = 22.0
    grid_limit_kw: float = 15.0
    battery_capacity_kwh: float = 20.0
    battery_soc_initial_pct: float = 50.0
    battery_soc_min_pct: float = 20.0
    battery_max_charge_kw: float = 5.0
    battery_max_discharge_kw: float = 5.0
    battery_charge_efficiency: float = 0.95
    battery_discharge_efficiency: float = 0.92
    solar_tariff_rs_kwh: float = 0.40
    battery_tariff_rs_kwh: float = 0.55
    grid_tariff_normal_rs_kwh: float = 0.80
    grid_tariff_peak_rs_kwh: float = 1.50
    # Fatores ilustrativos configuráveis, não fatores oficiais ou certificação de carbono.
    solar_emissions_kg_kwh: float = 0.05
    grid_emissions_kg_kwh: float = 0.50
    # Conservador: energia já armazenada não recebe crédito renovável sem prova de origem.
    battery_emissions_kg_kwh: float = 0.50

    def __post_init__(self):
        numeric_fields = (
            "hour", "duration_h", "pv_peak_kw", "weather_factor", "station_limit_kw", "grid_limit_kw",
            "battery_capacity_kwh", "battery_soc_initial_pct", "battery_soc_min_pct",
            "battery_max_charge_kw", "battery_max_discharge_kw", "battery_charge_efficiency",
            "battery_discharge_efficiency", "solar_tariff_rs_kwh", "battery_tariff_rs_kwh",
            "grid_tariff_normal_rs_kwh", "grid_tariff_peak_rs_kwh", "solar_emissions_kg_kwh",
            "grid_emissions_kg_kwh", "battery_emissions_kg_kwh",
        )
        for name in numeric_fields:
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"{name} precisa ser um número finito.")
        if not 0 <= self.hour <= 24:
            raise ValueError("A hora deve estar entre 0 e 24.")
        if self.duration_h <= 0:
            raise ValueError("A duração deve ser maior que zero.")
        if self.pv_peak_kw < 0 or self.station_limit_kw <= 0 or self.grid_limit_kw < 0:
            raise ValueError("Verifique potência solar, limite da estação e limite da rede.")
        if self.battery_capacity_kwh <= 0:
            raise ValueError("A capacidade da bateria deve ser maior que zero.")
        if not 0 <= self.weather_factor <= 1:
            raise ValueError("O fator climático deve estar entre 0 e 1.")
        if not 0 <= self.battery_soc_min_pct <= self.battery_soc_initial_pct <= 100:
            raise ValueError("O SOC deve estar entre 0–100% e ser maior ou igual à reserva mínima.")
        if self.battery_max_charge_kw < 0 or self.battery_max_discharge_kw < 0:
            raise ValueError("Os limites de carga/descarga da bateria não podem ser negativos.")
        if not 0 < self.battery_charge_efficiency <= 1 or not 0 < self.battery_discharge_efficiency <= 1:
            raise ValueError("A eficiência da bateria deve estar no intervalo (0, 1].")
        for name in ("solar_tariff_rs_kwh", "battery_tariff_rs_kwh", "grid_tariff_normal_rs_kwh", "grid_tariff_peak_rs_kwh", "solar_emissions_kg_kwh", "grid_emissions_kg_kwh", "battery_emissions_kg_kwh"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} não pode ser negativo.")


def _weighted_fair_allocation(capacities: dict[str, float], priorities: dict[str, float], total_kw: float) -> dict[str, float]:
    """Distribuição ponderada que nunca excede limite individual nem potência total."""
    allocation = {key: 0.0 for key in capacities}
    remaining = min(max(0.0, total_kw), sum(capacities.values()))
    active = {key for key, cap in capacities.items() if cap > 1e-9}
    while active and remaining > 1e-9:
        weight_sum = sum(priorities[k] for k in active)
        shares = {k: remaining * priorities[k] / weight_sum for k in active}
        saturated = [k for k in active if shares[k] >= capacities[k] - allocation[k] - 1e-9]
        if not saturated:
            for k, share in shares.items():
                allocation[k] += share
            remaining = 0.0
            break
        for k in saturated:
            addition = max(0.0, capacities[k] - allocation[k])
            allocation[k] += addition
            remaining -= addition
            active.remove(k)
    return {k: round(v, 6) for k, v in allocation.items()}


def _battery(config: SystemConfig) -> Bateria:
    return Bateria(
        capacidade_maxima=config.battery_capacity_kwh,
        carga_inicial_percentual=config.battery_soc_initial_pct,
        reserva_minima_percentual=config.battery_soc_min_pct,
        potencia_maxima_descarga_kw=config.battery_max_discharge_kw,
        potencia_maxima_carga_kw=config.battery_max_charge_kw,
        eficiencia_carga=config.battery_charge_efficiency,
        eficiencia_descarga=config.battery_discharge_efficiency,
    )


def simulate_session(requests: Iterable[EVRequest], config: SystemConfig | None = None, mode: str = "PV + Battery") -> dict:
    """Simula uma sessão de recarga com limites elétricos e partilha por prioridade."""
    config = config or SystemConfig()
    requests = list(requests)
    if not requests:
        raise ValueError("Informe ao menos um veículo para simular.")
    if mode not in MODOS_CARREGAMENTO:
        raise ValueError(f"Modo inválido. Escolha um de: {', '.join(MODOS_CARREGAMENTO)}.")
    ids = [str(item.vehicle_id) for item in requests]
    if len(set(ids)) != len(ids):
        raise ValueError("Os identificadores dos veículos devem ser únicos.")

    requested_power_by_vehicle = {
        str(ev.vehicle_id): min(ev.max_power_kw, ev.requested_energy_kwh / config.duration_h)
        for ev in requests
    }
    priorities = {str(ev.vehicle_id): ev.priority for ev in requests}
    demand_requested_kw = sum(requested_power_by_vehicle.values())
    target_kw = min(demand_requested_kw, config.station_limit_kw)
    pv_generation_kw = gerar_energia_solar(config.hour, config.pv_peak_kw, config.weather_factor)

    battery = _battery(config)
    battery_before_kwh, battery_before_pct = battery.status()
    solar_to_ev_kw = min(pv_generation_kw, target_kw)
    remaining_kw = max(0.0, target_kw - solar_to_ev_kw)
    battery_to_ev_kw = 0.0
    grid_to_ev_kw = 0.0

    def max_battery_power_kw() -> float:
        available_kwh = battery.energia_disponivel_para_descarga(config.duration_h)
        return min(config.battery_max_discharge_kw, available_kwh / config.duration_h)

    if mode == "PV + Battery":
        battery_to_ev_kw = min(remaining_kw, max_battery_power_kw())
        remaining_kw -= battery_to_ev_kw
        grid_to_ev_kw = min(remaining_kw, config.grid_limit_kw)
        remaining_kw -= grid_to_ev_kw
    elif mode == "PV Priority":
        # Modelo: PV primeiro; rede completa a carga quando habilitada nesta simulação;
        # a bateria não é descarregada para o veículo neste modo.
        grid_to_ev_kw = min(remaining_kw, config.grid_limit_kw)
        remaining_kw -= grid_to_ev_kw
    else:  # Fast: PV, rede até ao limite, bateria apenas quando a rede não basta.
        grid_to_ev_kw = min(remaining_kw, config.grid_limit_kw)
        remaining_kw -= grid_to_ev_kw
        battery_to_ev_kw = min(remaining_kw, max_battery_power_kw())
        remaining_kw -= battery_to_ev_kw

    energy_requested_kwh = sum(ev.requested_energy_kwh for ev in requests)
    station_limited_kw = max(0.0, demand_requested_kw - target_kw)

    battery_to_ev_kwh = battery.descarregar(battery_to_ev_kw * config.duration_h, config.duration_h)
    # Recalcula a potência com a energia efetivamente entregue pela bateria.
    battery_to_ev_kw = battery_to_ev_kwh / config.duration_h
    energy_delivered_kw = solar_to_ev_kw + battery_to_ev_kw + grid_to_ev_kw
    energy_delivered_kwh = energy_delivered_kw * config.duration_h
    # Energia pendente inclui o restante do pedido informado por veículo, não apenas a potência
    # que faltou neste intervalo. Isso permite simular recargas que precisam de mais de 1 hora.
    unmet_energy_kwh = max(0.0, sum(ev.requested_energy_kwh for ev in requests) - energy_delivered_kw * config.duration_h)
    station_limited_kw = max(0.0, demand_requested_kw - target_kw)
    supply_limited_kw = max(0.0, target_kw - energy_delivered_kw)

    solar_to_ev_kwh = solar_to_ev_kw * config.duration_h
    grid_to_ev_kwh = grid_to_ev_kw * config.duration_h
    solar_surplus_kw = max(0.0, pv_generation_kw - solar_to_ev_kw)
    solar_surplus_kwh = solar_surplus_kw * config.duration_h
    battery_charged_kwh, solar_input_unused_kwh = battery.carregar(solar_surplus_kwh, config.duration_h)
    battery_after_kwh, battery_after_pct = battery.status()

    peak_period = config.hour >= 18 or config.hour < 6 or config.hour == 24
    grid_tariff = config.grid_tariff_peak_rs_kwh if peak_period else config.grid_tariff_normal_rs_kwh
    source_tariff = {
        "solar": config.solar_tariff_rs_kwh,
        "bateria": config.battery_tariff_rs_kwh,
        "rede": grid_tariff,
    }
    bill = calcular_custo_misto(
        solar_to_ev_kwh, battery_to_ev_kwh, grid_to_ev_kwh, peak_period,
        tarifa_solar=config.solar_tariff_rs_kwh,
        tarifa_bateria=config.battery_tariff_rs_kwh,
        tarifa_rede=grid_tariff,
    )
    source_cost = {
        "solar": bill["custo_solar"],
        "bateria": bill["custo_bateria"],
        "rede": bill["custo_rede"],
    }
    total_cost = bill["custo_total"]
    all_grid_reference_cost = bill["custo_referencia_toda_rede"]
    savings = bill["economia_vs_toda_rede"]

    # Só a geração solar usada diretamente recebe crédito renovável conhecido.
    # A origem da energia já presente na bateria não é conhecida e, portanto,
    # é contabilizada conservadoramente pelo fator da rede.
    emissions = (
        solar_to_ev_kwh * config.solar_emissions_kg_kwh
        + battery_to_ev_kwh * config.battery_emissions_kg_kwh
        + grid_to_ev_kwh * config.grid_emissions_kg_kwh
    )
    emissions_all_grid = energy_delivered_kwh * config.grid_emissions_kg_kwh
    emissions_avoided = emissions_all_grid - emissions
    solar_share_pct = (solar_to_ev_kwh / energy_delivered_kwh * 100) if energy_delivered_kwh else 0.0

    allocations = _weighted_fair_allocation(requested_power_by_vehicle, priorities, energy_delivered_kw)
    vehicle_rows = []
    for ev in requests:
        vehicle_id = str(ev.vehicle_id)
        delivered_kw = allocations[vehicle_id]
        delivered_kwh = delivered_kw * config.duration_h
        if energy_delivered_kwh > 1e-9:
            fraction = delivered_kwh / energy_delivered_kwh
        else:
            fraction = 0.0
        per_ev_solar = solar_to_ev_kwh * fraction
        per_ev_battery = battery_to_ev_kwh * fraction
        per_ev_grid = grid_to_ev_kwh * fraction
        per_ev_cost = (
            per_ev_solar * config.solar_tariff_rs_kwh
            + per_ev_battery * config.battery_tariff_rs_kwh
            + per_ev_grid * grid_tariff
        )
        vehicle_rows.append({
            "veiculo": vehicle_id,
            "potencia_atendida_kw": round(delivered_kw, 3),
            "energia_entregue_kwh": round(delivered_kwh, 3),
            "energia_solicitada_kwh": round(ev.requested_energy_kwh, 3),
            "energia_nao_atendida_kwh": round(max(0.0, ev.requested_energy_kwh - delivered_kwh), 3),
            "solar_kwh": round(per_ev_solar, 3),
            "bateria_kwh": round(per_ev_battery, 3),
            "rede_kwh": round(per_ev_grid, 3),
            "custo_rs": round(per_ev_cost, 2),
            "prioridade": ev.priority,
        })

    # Reconcilia os centavos por veículo com o total da sessão, usando o maior resto.
    # Assim, a soma dos custos exibidos por veículo corresponde ao custo total arredondado.
    raw_costs = [row["custo_rs"] for row in vehicle_rows]
    cents = [int(round(cost * 100)) for cost in raw_costs]
    target_cents = int(round(total_cost * 100))
    difference = target_cents - sum(cents)
    if difference > 0:
        order = sorted(range(len(raw_costs)), key=lambda i: raw_costs[i] * 100 - cents[i], reverse=True)
        for idx in range(difference):
            cents[order[idx % len(order)]] += 1
    elif difference < 0:
        order = sorted(range(len(raw_costs)), key=lambda i: raw_costs[i] * 100 - cents[i])
        for idx in range(-difference):
            cents[order[idx % len(order)]] -= 1
    for row, cents_value in zip(vehicle_rows, cents):
        row["custo_rs"] = round(cents_value / 100, 2)

    alerts = []
    if station_limited_kw > 1e-6:
        alerts.append(f"Limite da estação ativo: {station_limited_kw:.2f} kW da demanda solicitada não cabem no limite configurado.")
    if supply_limited_kw > 1e-6:
        alerts.append(f"Oferta insuficiente: {supply_limited_kw:.2f} kW ficaram sem atendimento no intervalo simulado.")
    if battery_to_ev_kwh > 0:
        alerts.append("Bateria usada respeitando potência máxima, eficiência e reserva mínima de SOC.")
    if battery_charged_kwh > 0:
        alerts.append(f"Excedente solar armazenou {battery_charged_kwh:.2f} kWh na bateria (após perdas de carga).")
    if peak_period:
        alerts.append("Tarifa de rede de pico aplicada conforme janela didática configurada (18h–6h).")
    if unmet_energy_kwh > 1e-6 and station_limited_kw <= 1e-6 and supply_limited_kw <= 1e-6:
        alerts.append("Há energia solicitada ainda pendente porque a potência individual/duração não permite concluir o pedido neste intervalo.")
    if not alerts:
        alerts.append("Demanda atendida dentro dos limites configurados.")

    return {
        "modo": mode,
        "hora": config.hour,
        "duracao_h": config.duration_h,
        "fator_clima": config.weather_factor,
        "geracao_solar_kw": round(pv_generation_kw, 3),
        "demanda_solicitada_kw": round(demand_requested_kw, 3),
        "demanda_limitada_estacao_kw": round(target_kw, 3),
        "potencia_atendida_kw": round(energy_delivered_kw, 3),
        "energia_entregue_kwh": round(energy_delivered_kwh, 3),
        "energia_solicitada_kwh": round(energy_requested_kwh, 3),
        "energia_nao_atendida_kwh": round(unmet_energy_kwh, 3),
        "limitacao_estacao_kw": round(station_limited_kw, 3),
        "limitacao_oferta_kw": round(supply_limited_kw, 3),
        "solar_usada_kw": round(solar_to_ev_kw, 3),
        "solar_usada_kwh": round(solar_to_ev_kwh, 3),
        "solar_excedente_kwh": round(solar_surplus_kwh, 3),
        "bateria_fornecida_kw": round(battery_to_ev_kw, 3),
        "bateria_fornecida_kwh": round(battery_to_ev_kwh, 3),
        "bateria_carregada_kwh": round(battery_charged_kwh, 3),
        "excedente_solar_nao_armazenado_kwh": round(solar_input_unused_kwh, 3),
        "rede_importada_kw": round(grid_to_ev_kw, 3),
        "rede_importada_kwh": round(grid_to_ev_kwh, 3),
        "battery_soc_before_pct": round(battery_before_pct, 2),
        "battery_soc_after_pct": round(battery_after_pct, 2),
        "battery_energy_before_kwh": round(battery_before_kwh, 3),
        "battery_energy_after_kwh": round(battery_after_kwh, 3),
        "participacao_solar_direta_pct": round(solar_share_pct, 2),
        "custo_solar_rs": round(source_cost["solar"], 2),
        "custo_bateria_rs": round(source_cost["bateria"], 2),
        "custo_rede_rs": round(source_cost["rede"], 2),
        "custo_total_rs": round(total_cost, 2),
        "custo_referencia_toda_rede_rs": round(all_grid_reference_cost, 2),
        "economia_estimada_rs": round(savings, 2),
        "emissoes_estimadas_kg_co2e": round(emissions, 3),
        "emissoes_referencia_toda_rede_kg_co2e": round(emissions_all_grid, 3),
        "emissoes_evitas_estimadas_kg_co2e": round(emissions_avoided, 3),
        "tarifa_rede_rs_kwh": round(grid_tariff, 2),
        "tarifas_didaticas_rs_kwh": source_tariff,
        "veiculos": vehicle_rows,
        "alertas": alerts,
        "aviso": "SIMULAÇÃO: sem telemetria ou comando real de equipamento GoodWe. Tarifas e fatores de emissão são hipóteses didáticas.",
    }


def compare_modes(requests: Iterable[EVRequest], config: SystemConfig | None = None) -> list[dict]:
    """Executa cada modo a partir do mesmo estado inicial de bateria."""
    config = config or SystemConfig()
    requests = list(requests)
    return [simulate_session(requests, config, mode) for mode in MODOS_CARREGAMENTO]


def recommend_mode(requests: Iterable[EVRequest], config: SystemConfig | None = None) -> tuple[str, list[dict]]:
    resultados = compare_modes(list(requests), config)
    return recomendar_modo(resultados), resultados
