"""Motor decisório explicável; não é um modelo de aprendizado de máquina."""
from __future__ import annotations

MODOS_CARREGAMENTO = ("PV Priority", "PV + Battery", "Fast")


def recomendar_modo(resultados_por_modo: list[dict]) -> str:
    """Escolhe a estratégia por critérios transparentes: atendimento, custo e emissões.

    Primeiro minimiza a energia não atendida; em empate, o custo; por último,
    as emissões estimadas. Os resultados recebidos devem ter sido simulados com
    o mesmo cenário e estado inicial de bateria.
    """
    if not resultados_por_modo:
        raise ValueError("É necessário fornecer ao menos um resultado para recomendar.")
    melhor = min(
        resultados_por_modo,
        key=lambda r: (
            round(float(r.get("energia_nao_atendida_kwh", 0.0)), 6),
            round(float(r.get("custo_total_rs", 0.0)), 6),
            round(float(r.get("emissoes_estimadas_kg_co2e", 0.0)), 6),
        ),
    )
    return str(melhor["modo"])


def explicar_recomendacao(resultado: dict) -> str:
    if resultado["energia_nao_atendida_kwh"] > 1e-6:
        return (
            "A recomendação reduz a energia não atendida primeiro. Ainda há demanda pendente; "
            "considere reduzir a quantidade de veículos, aumentar a janela de recarga ou rever limites."
        )
    return (
        "Entre os modos simulados, esta estratégia atende a demanda configurada com o menor custo "
        "estimado; as emissões são critério de desempate. A escolha é explicável e reproduzível."
    )


def decidir_estrategia(geracao_solar, carga_bateria_percentual, veiculos_conectados, demanda_total):
    """Assinatura legada da Sprint 3, mantida para compatibilidade."""
    alertas = []
    fator_reducao = 1.0
    if veiculos_conectados <= 0:
        raise ValueError("A quantidade de veículos deve ser maior que zero.")
    if demanda_total <= geracao_solar:
        fonte = "Solar"
        alertas.append("A geração solar simulada cobre a demanda informada.")
    elif carga_bateria_percentual > 20:
        fonte = "Solar + Bateria + Rede"
        alertas.append("A lógica legada recomenda considerar bateria e rede após a prioridade solar.")
    else:
        fonte = "Solar + Rede"
        alertas.append("A reserva da bateria está baixa; evitar descarga abaixo do limite configurado.")
    if veiculos_conectados > 3:
        fator_reducao = 0.8
        alertas.append("A versão legada sinalizaria redução preventiva; a Sprint 4 calcula limites reais.")
    else:
        alertas.append("A versão legada não sinaliza redução pelo número de veículos.")
    return fonte, fator_reducao, alertas
