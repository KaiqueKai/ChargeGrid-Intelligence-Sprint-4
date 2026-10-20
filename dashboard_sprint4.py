"""Painel interativo da Sprint 4 (Streamlit)."""
from __future__ import annotations
import json
import pandas as pd
import streamlit as st

from ai_module import MODOS_CARREGAMENTO, explicar_recomendacao
from assistant_module import responder_pergunta
from dashboard import gerar_dashboard_sprint4
from energy_manager import EVRequest, SystemConfig, compare_modes, recommend_mode, simulate_session

st.set_page_config(page_title="ChargeGrid Intelligence | Sprint 4", page_icon="⚡", layout="wide")
st.title("⚡ ChargeGrid Intelligence")
st.subheader("Sprint 4 — Gestão integrada de energia para recarga de veículos elétricos")
st.warning("Modo demonstração: os dados são simulados. O painel não se conecta nem envia comandos a equipamentos GoodWe.")

with st.sidebar:
    st.header("Cenário de simulação")
    n_vehicles = st.number_input("Veículos conectados", min_value=1, max_value=12, value=3, step=1)
    hour = st.slider("Hora simulada", min_value=0, max_value=24, value=12)
    duration = st.number_input("Duração do intervalo (h)", min_value=0.25, max_value=24.0, value=1.0, step=0.25)
    pv_peak = st.number_input("Potência fotovoltaica de referência (kW)", min_value=0.0, max_value=500.0, value=15.0, step=1.0)
    weather = st.slider("Fator climático (1 = céu limpo)", min_value=0.0, max_value=1.0, value=0.85, step=0.05)
    station_limit = st.number_input("Limite da estação (kW)", min_value=1.0, max_value=500.0, value=22.0, step=1.0)
    grid_limit = st.number_input("Importação máxima da rede (kW)", min_value=0.0, max_value=500.0, value=15.0, step=1.0)
    soc = st.slider("SOC inicial da bateria (%)", min_value=20, max_value=100, value=50)
    mode_choice = st.selectbox("Estratégia de carregamento", ["AUTO — recomendar"] + list(MODOS_CARREGAMENTO))

    st.caption("Para o cenário padrão de 1 hora, limite cada veículo a 7 kW e solicite até 7 kWh.")
    vehicle_inputs = []
    for i in range(int(n_vehicles)):
        with st.expander(f"Configuração do veículo {i + 1}", expanded=(i == 0)):
            max_power = st.number_input(f"Potência máxima EV {i + 1} (kW)", min_value=0.1, max_value=22.0, value=7.0, step=0.5, key=f"p{i}")
            energy = st.number_input(f"Energia solicitada EV {i + 1} (kWh)", min_value=0.1, max_value=250.0, value=7.0, step=0.5, key=f"e{i}")
            priority = st.number_input(f"Prioridade EV {i + 1}", min_value=0.1, max_value=5.0, value=1.0, step=0.1, key=f"w{i}")
            vehicle_inputs.append((max_power, energy, priority))

requests = [EVRequest(str(i + 1), p, e, w) for i, (p, e, w) in enumerate(vehicle_inputs)]
config = SystemConfig(
    hour=float(hour), duration_h=float(duration), pv_peak_kw=float(pv_peak), weather_factor=float(weather),
    station_limit_kw=float(station_limit), grid_limit_kw=float(grid_limit), battery_soc_initial_pct=float(soc),
)

comparisons = compare_modes(requests, config)
if mode_choice.startswith("AUTO"):
    selected_mode, _ = recommend_mode(requests, config)
else:
    selected_mode = mode_choice
result = next(row for row in comparisons if row["modo"] == selected_mode)

st.caption(f"Modo aplicado: **{selected_mode}** · Hora: {hour}:00 · Intervalo: {duration:g} h")
cols = st.columns(4)
cols[0].metric("Energia entregue", f"{result['energia_entregue_kwh']:.2f} kWh")
cols[1].metric("Potência atendida", f"{result['potencia_atendida_kw']:.2f} kW")
cols[2].metric("Custo demonstrativo", f"R$ {result['custo_total_rs']:.2f}", delta=f"R$ {result['economia_estimada_rs']:.2f} vs. rede", delta_color="normal")
cols[3].metric("Participação solar direta", f"{result['participacao_solar_direta_pct']:.1f}%")

left, right = st.columns(2)
with left:
    st.markdown("#### Fluxo de energia")
    source_df = pd.DataFrame({"Fonte": ["Solar direta", "Bateria", "Rede"], "Energia (kWh)": [result["solar_usada_kwh"], result["bateria_fornecida_kwh"], result["rede_importada_kwh"]]}).set_index("Fonte")
    st.bar_chart(source_df)
    st.write(f"Geração solar disponível: **{result['geracao_solar_kw']:.2f} kW**")
    st.write(f"Carga da bateria: **{result['battery_soc_before_pct']:.1f}% → {result['battery_soc_after_pct']:.1f}%**")
    if result["bateria_carregada_kwh"] > 0:
        st.write(f"Excedente armazenado: **{result['bateria_carregada_kwh']:.2f} kWh**")
with right:
    st.markdown("#### Atendimento por veículo")
    vehicle_df = pd.DataFrame(result["veiculos"])
    st.dataframe(vehicle_df.rename(columns={
        "veiculo": "Veículo", "potencia_atendida_kw": "Potência (kW)", "energia_entregue_kwh": "Entregue (kWh)",
        "energia_solicitada_kwh": "Solicitado (kWh)", "energia_nao_atendida_kwh": "Pendente (kWh)",
        "solar_kwh": "Solar (kWh)", "bateria_kwh": "Bateria (kWh)", "rede_kwh": "Rede (kWh)", "custo_rs": "Custo (R$)", "prioridade": "Prioridade"
    }), width="stretch", hide_index=True)

st.markdown("#### Comparação das estratégias")
comparison_df = pd.DataFrame([{
    "Modo": row["modo"], "Entregue (kWh)": row["energia_entregue_kwh"], "Pendente (kWh)": row["energia_nao_atendida_kwh"],
    "Solar direta (%)": row["participacao_solar_direta_pct"], "Custo (R$)": row["custo_total_rs"],
    "Economia estimada (R$)": row["economia_estimada_rs"], "CO₂e estimado (kg)": row["emissoes_estimadas_kg_co2e"],
    "SOC final (%)": row["battery_soc_after_pct"],
} for row in comparisons])
st.dataframe(comparison_df, width="stretch", hide_index=True)
st.info("Recomendação: " + explicar_recomendacao(result))

st.markdown("#### Alertas do controlador")
for alert in result["alertas"]:
    st.write(f"• {alert}")

st.markdown("#### Impacto ambiental e financeiro")
a, b, c = st.columns(3)
a.metric("Emissões estimadas", f"{result['emissoes_estimadas_kg_co2e']:.3f} kg CO₂e")
b.metric("Emissões evitadas estimadas", f"{result['emissoes_evitas_estimadas_kg_co2e']:.3f} kg CO₂e")
c.metric("Custo se toda energia fosse da rede", f"R$ {result['custo_referencia_toda_rede_rs']:.2f}")
st.caption("Tarifas e fatores de emissão são hipóteses didáticas e editáveis no código. A energia já armazenada na bateria não recebe crédito renovável por falta de rastreamento de origem.")
st.caption("Interpretação das emissões: neste modelo, a bateria e a rede usam o mesmo fator ilustrativo (0,50 kg CO₂e/kWh), porque a origem histórica da energia armazenada não é rastreada. Assim, substituir energia da rede por energia da bateria pode reduzir o custo estimado sem alterar as emissões calculadas.")

st.markdown("#### Assistente virtual do ChargeGrid")
st.caption("Assistente local baseado em regras. Interpreta apenas a simulação atual; não usa API externa nem representa telemetria real.")
question = st.text_input("Pergunte sobre energia solar, bateria, rede, custos, CO₂ ou veículos", key="assistant_question")
if st.button("Consultar assistente", key="assistant_submit"):
    st.info(responder_pergunta(question, result, comparisons))

st.markdown("#### Exportar resultados")
st.download_button("Baixar simulação JSON", data=json.dumps(result, ensure_ascii=False, indent=2), file_name="chargegrid_sprint4_resultado.json", mime="application/json")
st.download_button("Baixar comparação CSV", data=comparison_df.to_csv(index=False).encode("utf-8-sig"), file_name="chargegrid_sprint4_comparacao.csv", mime="text/csv")

try:
    image_path = gerar_dashboard_sprint4(result, "reports/dashboard_sprint4_painel.png")
    st.image(str(image_path), caption="Resumo estático exportável da sessão simulada", width="stretch")
except Exception as exc:
    st.caption(f"O painel interativo continua funcionando; não foi possível gerar o PNG nesta execução: {exc}")
