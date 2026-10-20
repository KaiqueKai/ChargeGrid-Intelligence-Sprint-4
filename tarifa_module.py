"""Tarifação por fonte para fins demonstrativos, com hipóteses configuráveis.

Estes preços são valores didáticos da simulação e NÃO são tarifas oficiais GoodWe,
preços de mercado, tarifas reguladas ou proposta comercial.
"""
from __future__ import annotations

TARIFA_SOLAR_R_KWH = 0.40
TARIFA_BATERIA_R_KWH = 0.55
TARIFA_REDE_NORMAL_R_KWH = 0.80
TARIFA_REDE_PICO_R_KWH = 1.50


def tarifas_da_sessao(horario_pico: bool = False) -> dict[str, float]:
    return {
        "solar": TARIFA_SOLAR_R_KWH,
        "bateria": TARIFA_BATERIA_R_KWH,
        "rede": TARIFA_REDE_PICO_R_KWH if horario_pico else TARIFA_REDE_NORMAL_R_KWH,
    }


def calcular_tarifa(fonte_energia: str, horario_pico: bool = False) -> tuple[float, str]:
    """Compatibilidade com a função usada na Sprint 3."""
    fonte = fonte_energia.strip().lower()
    if fonte == "solar":
        return TARIFA_SOLAR_R_KWH, "Solar (valor didático)"
    if "bateria" in fonte and "rede" not in fonte:
        return TARIFA_BATERIA_R_KWH, "Bateria (valor didático)"
    if horario_pico:
        return TARIFA_REDE_PICO_R_KWH, "Rede em horário de pico (valor didático)"
    return TARIFA_REDE_NORMAL_R_KWH, "Rede em horário normal (valor didático)"


def calcular_custo_misto(
    solar_kwh: float,
    bateria_kwh: float,
    rede_kwh: float,
    horario_pico: bool = False,
    *,
    tarifa_solar: float | None = None,
    tarifa_bateria: float | None = None,
    tarifa_rede: float | None = None,
) -> dict[str, float]:
    """Calcula a conta por origem de energia com valores didáticos configuráveis."""
    valores = (solar_kwh, bateria_kwh, rede_kwh)
    if any(v < 0 for v in valores):
        raise ValueError("O consumo por fonte não pode ser negativo.")
    tarifas_padrao = tarifas_da_sessao(horario_pico)
    tarifa_solar = tarifas_padrao["solar"] if tarifa_solar is None else tarifa_solar
    tarifa_bateria = tarifas_padrao["bateria"] if tarifa_bateria is None else tarifa_bateria
    tarifa_rede = tarifas_padrao["rede"] if tarifa_rede is None else tarifa_rede
    if any(t < 0 for t in (tarifa_solar, tarifa_bateria, tarifa_rede)):
        raise ValueError("As tarifas não podem ser negativas.")
    parcelas = {
        "custo_solar": solar_kwh * tarifa_solar,
        "custo_bateria": bateria_kwh * tarifa_bateria,
        "custo_rede": rede_kwh * tarifa_rede,
    }
    parcelas["custo_total"] = sum(parcelas.values())
    parcelas["custo_referencia_toda_rede"] = (solar_kwh + bateria_kwh + rede_kwh) * tarifa_rede
    parcelas["economia_vs_toda_rede"] = parcelas["custo_referencia_toda_rede"] - parcelas["custo_total"]
    return {k: round(v, 4) for k, v in parcelas.items()}
