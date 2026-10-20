"""Assistente local e explicável para interpretar o resultado da simulação.

Não usa LLM, API externa nem telemetria. As respostas são montadas a partir
somente do resultado calculado e das hipóteses declaradas pelo projeto.
"""
from __future__ import annotations
import unicodedata


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(caractere for caractere in texto if not unicodedata.combining(caractere))


def responder_pergunta(pergunta: str, resultado: dict, comparacoes: list[dict] | None = None) -> str:
    """Responde perguntas comuns sobre a sessão atualmente simulada."""
    q = _normalizar(pergunta.strip())
    if not q:
        return "Digite uma pergunta sobre geração solar, bateria, rede, custo, emissões, veículos ou modo recomendado."

    if any(term in q for term in ("solar", "sol", "fotovolta", "painel")):
        share = resultado["participacao_solar_direta_pct"]
        return (
            f"A geração solar simulada está em {resultado['geracao_solar_kw']:.2f} kW. "
            f"Os veículos usaram diretamente {resultado['solar_usada_kwh']:.2f} kWh de solar, "
            f"equivalentes a {share:.1f}% da energia entregue nesta janela. "
            "O cálculo usa uma curva solar didática com fator climático configurável; não é leitura de sensor real."
        )

    if any(term in q for term in ("bateria", "soc", "armazen", "reserva")):
        return (
            f"A bateria começou em {resultado['battery_soc_before_pct']:.1f}% "
            f"({resultado['battery_energy_before_kwh']:.2f} kWh) e terminou em "
            f"{resultado['battery_soc_after_pct']:.1f}% ({resultado['battery_energy_after_kwh']:.2f} kWh). "
            f"Entregou {resultado['bateria_fornecida_kwh']:.2f} kWh aos veículos e armazenou "
            f"{resultado['bateria_carregada_kwh']:.2f} kWh de excedente solar. A descarga respeita reserva, "
            "potência máxima e eficiência configuradas."
        )

    if any(term in q for term in ("custo", "preco", "tarifa", "econom", "dinheiro", "valor")):
        return (
            f"O custo demonstrativo foi R$ {resultado['custo_total_rs']:.2f}; a referência didática, "
            f"usando tarifa de rede para toda a energia entregue, foi R$ {resultado['custo_referencia_toda_rede_rs']:.2f}. "
            f"A diferença estimada é R$ {resultado['economia_estimada_rs']:.2f}. "
            "Tarifas são premissas editáveis no código, não preços oficiais nem economia medida."
        )

    if any(term in q for term in ("co2", "emissao", "carbon", "sustent", "ambient")):
        return (
            f"As emissões calculadas são {resultado['emissoes_estimadas_kg_co2e']:.3f} kg CO2e; "
            f"a diferença para a referência de toda a energia pela rede é "
            f"{resultado['emissoes_evitas_estimadas_kg_co2e']:.3f} kg CO2e. "
            "São estimativas a partir de fatores didáticos. A energia já presente na bateria é contabilizada "
            "conservadoramente com o fator de rede porque o protótipo não rastreia sua origem."
        )

    if any(term in q for term in ("rede", "concessionaria", "importa", "grid")):
        return (
            f"A rede forneceu {resultado['rede_importada_kwh']:.2f} kWh, com potência de "
            f"{resultado['rede_importada_kw']:.2f} kW. O limite configurado de importação é respeitado; "
            "a janela tarifária de pico e os valores de tarifa são hipóteses da simulação."
        )

    if any(term in q for term in ("veiculo", "carro", "recarga", "pedido", "pendente", "potencia")):
        detalhes = "; ".join(
            f"EV {row['veiculo']}: {row['energia_entregue_kwh']:.2f} kWh entregues, "
            f"{row['energia_nao_atendida_kwh']:.2f} kWh pendentes, R$ {row['custo_rs']:.2f}"
            for row in resultado["veiculos"]
        )
        return f"Distribuição por veículo: {detalhes}. A potência foi rateada respeitando os limites por veículo e da estação."

    if any(term in q for term in ("modo", "recomend", "estrateg", "fast", "prioridade")):
        if comparacoes:
            comparacao = "; ".join(
                f"{row['modo']}: pendente {row['energia_nao_atendida_kwh']:.2f} kWh, "
                f"custo R$ {row['custo_total_rs']:.2f}"
                for row in comparacoes
            )
        else:
            comparacao = f"modo atual {resultado['modo']}, custo R$ {resultado['custo_total_rs']:.2f}"
        return (
            f"O modo selecionado é {resultado['modo']}. A recomendação prioriza menor energia pendente, "
            "depois menor custo e, em empate, menores emissões estimadas. Comparação: " + comparacao + "."
        )

    return (
        f"Nesta simulação foram entregues {resultado['energia_entregue_kwh']:.2f} kWh; "
        f"o modo selecionado é {resultado['modo']} e o custo demonstrativo é R$ {resultado['custo_total_rs']:.2f}. "
        "Pergunte, por exemplo: 'Como foi usada a energia solar?', 'Como ficou a bateria?', "
        "'Quanto economizamos?' ou 'Compare os modos'."
    )
