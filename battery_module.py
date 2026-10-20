"""Modelo de bateria com limites de potência, eficiência e reserva de SOC."""
from __future__ import annotations


class Bateria:
    def __init__(
        self,
        capacidade_maxima: float = 20.0,
        carga_inicial_percentual: float = 50.0,
        reserva_minima_percentual: float = 20.0,
        potencia_maxima_descarga_kw: float = 5.0,
        potencia_maxima_carga_kw: float = 5.0,
        eficiencia_carga: float = 0.95,
        eficiencia_descarga: float = 0.92,
    ) -> None:
        if capacidade_maxima <= 0:
            raise ValueError("A capacidade da bateria deve ser maior que zero.")
        if not 0 <= carga_inicial_percentual <= 100:
            raise ValueError("A carga inicial deve estar entre 0 e 100%.")
        if not 0 <= reserva_minima_percentual <= 100:
            raise ValueError("A reserva mínima deve estar entre 0 e 100%.")
        if carga_inicial_percentual < reserva_minima_percentual:
            raise ValueError("A carga inicial não pode ficar abaixo da reserva mínima.")
        if potencia_maxima_descarga_kw < 0 or potencia_maxima_carga_kw < 0:
            raise ValueError("Os limites de potência da bateria não podem ser negativos.")
        if not 0 < eficiencia_carga <= 1 or not 0 < eficiencia_descarga <= 1:
            raise ValueError("As eficiências devem estar no intervalo (0, 1].")

        self.capacidade_maxima = float(capacidade_maxima)
        self.carga_atual = self.capacidade_maxima * carga_inicial_percentual / 100
        self.reserva_minima_kwh = self.capacidade_maxima * reserva_minima_percentual / 100
        self.potencia_maxima_descarga_kw = float(potencia_maxima_descarga_kw)
        self.potencia_maxima_carga_kw = float(potencia_maxima_carga_kw)
        self.eficiencia_carga = float(eficiencia_carga)
        self.eficiencia_descarga = float(eficiencia_descarga)

    def energia_disponivel_para_descarga(self, duracao_h: float = 1.0) -> float:
        """Energia AC (kWh) que pode ser entregue sem violar a reserva/limite."""
        if duracao_h <= 0:
            raise ValueError("A duração deve ser maior que zero.")
        energia_interna_disponivel = max(0.0, self.carga_atual - self.reserva_minima_kwh)
        por_estoque = energia_interna_disponivel * self.eficiencia_descarga
        por_potencia = self.potencia_maxima_descarga_kw * duracao_h
        return max(0.0, min(por_estoque, por_potencia))

    def descarregar(self, energia_solicitada_kwh: float, duracao_h: float = 1.0) -> float:
        """Entrega energia AC (kWh); desconta as perdas da energia interna."""
        if energia_solicitada_kwh < 0:
            raise ValueError("A energia solicitada para descarga não pode ser negativa.")
        if duracao_h <= 0:
            raise ValueError("A duração deve ser maior que zero.")
        energia_entregue = min(
            energia_solicitada_kwh,
            self.energia_disponivel_para_descarga(duracao_h),
        )
        energia_interna_consumida = energia_entregue / self.eficiencia_descarga
        self.carga_atual = max(self.reserva_minima_kwh, self.carga_atual - energia_interna_consumida)
        return round(energia_entregue, 6)

    def carregar(self, energia_solar_disponivel_kwh: float, duracao_h: float = 1.0) -> tuple[float, float]:
        """Armazena excedente solar. Retorna (energia armazenada, entrada não usada)."""
        if energia_solar_disponivel_kwh < 0:
            raise ValueError("A energia disponível para carga não pode ser negativa.")
        if duracao_h <= 0:
            raise ValueError("A duração deve ser maior que zero.")
        espaco_interno = max(0.0, self.capacidade_maxima - self.carga_atual)
        limite_por_espaco = espaco_interno / self.eficiencia_carga
        entrada_aceita = min(
            energia_solar_disponivel_kwh,
            self.potencia_maxima_carga_kw * duracao_h,
            limite_por_espaco,
        )
        armazenada = entrada_aceita * self.eficiencia_carga
        self.carga_atual = min(self.capacidade_maxima, self.carga_atual + armazenada)
        nao_usada = max(0.0, energia_solar_disponivel_kwh - entrada_aceita)
        return round(armazenada, 6), round(nao_usada, 6)

    def status(self) -> tuple[float, float]:
        percentual = (self.carga_atual / self.capacidade_maxima) * 100
        return round(self.carga_atual, 3), round(percentual, 2)
