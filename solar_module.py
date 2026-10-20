"""Modelo didático e reproduzível de geração fotovoltaica.

Os valores representam uma instalação hipotética, não a telemetria de um inversor GoodWe.
"""
from __future__ import annotations
import math


def gerar_energia_solar(
    hora: float,
    potencia_maxima_kw: float = 15.0,
    fator_clima: float = 0.85,
) -> float:
    """Retorna potência fotovoltaica estimada (kW) para hora 0–24.

    Usa uma curva senoidal entre 6h e 18h e um fator climático entre 0 e 1.
    Não usa aleatoriedade: a mesma entrada gera o mesmo resultado, facilitando
    auditoria, testes e comparação entre estratégias.
    """
    if not 0 <= hora <= 24:
        raise ValueError("A hora deve estar entre 0 e 24.")
    if potencia_maxima_kw < 0:
        raise ValueError("A potência máxima solar não pode ser negativa.")
    if not 0 <= fator_clima <= 1:
        raise ValueError("O fator climático deve estar entre 0 e 1.")
    if hora <= 6 or hora >= 18 or potencia_maxima_kw == 0 or fator_clima == 0:
        return 0.0
    curva = math.sin(math.pi * (hora - 6) / 12)
    return round(potencia_maxima_kw * curva * fator_clima, 3)
