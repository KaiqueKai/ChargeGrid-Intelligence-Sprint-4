import unittest

from battery_module import Bateria
from assistant_module import responder_pergunta
from energy_manager import EVRequest, SystemConfig, compare_modes, simulate_session
from solar_module import gerar_energia_solar


class TestChargeGridSprint4(unittest.TestCase):
    def setUp(self):
        self.config = SystemConfig(hour=12, duration_h=1, weather_factor=0.85)
        self.vehicles = [EVRequest("EV1", 7, 7), EVRequest("EV2", 7, 7), EVRequest("EV3", 7, 7)]

    def test_curva_solar_pico_ao_meio_dia(self):
        self.assertEqual(gerar_energia_solar(0), 0.0)
        self.assertEqual(gerar_energia_solar(6), 0.0)
        self.assertEqual(gerar_energia_solar(18), 0.0)
        self.assertAlmostEqual(gerar_energia_solar(12), 12.75, places=2)

    def test_potencia_atendida_nao_excede_limite_estacao(self):
        cfg = SystemConfig(hour=12, station_limit_kw=10, grid_limit_kw=15)
        result = simulate_session(self.vehicles, cfg, "PV + Battery")
        self.assertLessEqual(result["potencia_atendida_kw"], cfg.station_limit_kw + 1e-6)

    def test_importacao_rede_nao_excede_limite(self):
        cfg = SystemConfig(hour=0, station_limit_kw=22, grid_limit_kw=4, battery_soc_initial_pct=20)
        result = simulate_session(self.vehicles, cfg, "PV Priority")
        self.assertLessEqual(result["rede_importada_kw"], cfg.grid_limit_kw + 1e-6)

    def test_reserva_da_bateria_e_respeitada(self):
        cfg = SystemConfig(hour=0, grid_limit_kw=0, station_limit_kw=22, battery_soc_initial_pct=25,
                           battery_soc_min_pct=20, battery_max_discharge_kw=20)
        result = simulate_session(self.vehicles, cfg, "PV + Battery")
        self.assertGreaterEqual(result["battery_soc_after_pct"], cfg.battery_soc_min_pct - 1e-6)

    def test_bateria_carrega_com_excedente_solar(self):
        cfg = SystemConfig(hour=12, station_limit_kw=5, grid_limit_kw=15, battery_soc_initial_pct=50)
        result = simulate_session([EVRequest("EV1", 3, 3)], cfg, "PV + Battery")
        self.assertGreater(result["bateria_carregada_kwh"], 0)
        self.assertGreaterEqual(result["battery_soc_after_pct"], result["battery_soc_before_pct"])

    def test_distribuicao_respeita_limites_individuais(self):
        cfg = SystemConfig(hour=0, station_limit_kw=4, grid_limit_kw=4, battery_soc_initial_pct=20)
        requests = [EVRequest("EV1", 1.5, 7), EVRequest("EV2", 7, 7), EVRequest("EV3", 7, 7)]
        result = simulate_session(requests, cfg, "PV Priority")
        ev1 = next(row for row in result["veiculos"] if row["veiculo"] == "EV1")
        self.assertLessEqual(ev1["potencia_atendida_kw"], 1.5 + 1e-6)
        self.assertLessEqual(sum(row["potencia_atendida_kw"] for row in result["veiculos"]), 4 + 1e-6)

    def test_fontes_somam_energia_entregue(self):
        result = simulate_session(self.vehicles, self.config, "PV + Battery")
        total = result["solar_usada_kwh"] + result["bateria_fornecida_kwh"] + result["rede_importada_kwh"]
        self.assertAlmostEqual(total, result["energia_entregue_kwh"], places=3)

    def test_fontes_por_veiculo_somam_totais(self):
        result = simulate_session(self.vehicles, self.config, "PV + Battery")
        for key, result_key in [("solar_kwh", "solar_usada_kwh"), ("bateria_kwh", "bateria_fornecida_kwh"), ("rede_kwh", "rede_importada_kwh")]:
            self.assertAlmostEqual(sum(row[key] for row in result["veiculos"]), result[result_key], places=2)

    def test_modo_pv_priority_nao_descarrega_bateria(self):
        cfg = SystemConfig(hour=0, grid_limit_kw=0, battery_soc_initial_pct=80)
        result = simulate_session(self.vehicles, cfg, "PV Priority")
        self.assertEqual(result["bateria_fornecida_kwh"], 0)
        self.assertEqual(result["battery_soc_after_pct"], result["battery_soc_before_pct"])

    def test_modo_pv_battery_reduz_energia_nao_atendida_vs_pv_priority(self):
        cfg = SystemConfig(hour=0, grid_limit_kw=0, battery_soc_initial_pct=80, station_limit_kw=22)
        results = {r["modo"]: r for r in compare_modes(self.vehicles, cfg)}
        self.assertLess(results["PV + Battery"]["energia_entregue_kwh"], 22.01)
        self.assertGreater(results["PV + Battery"]["energia_entregue_kwh"], results["PV Priority"]["energia_entregue_kwh"])

    def test_modo_automatico_retorna_modo_valido(self):
        results = compare_modes(self.vehicles, self.config)
        chosen = min(results, key=lambda r: (r["energia_nao_atendida_kwh"], r["custo_total_rs"], r["emissoes_estimadas_kg_co2e"]))
        self.assertIn(chosen["modo"], [r["modo"] for r in results])

    def test_tarifas_e_emissoes_nao_negativas(self):
        result = simulate_session(self.vehicles, self.config, "PV + Battery")
        self.assertGreaterEqual(result["custo_total_rs"], 0)
        self.assertGreaterEqual(result["emissoes_estimadas_kg_co2e"], 0)

    def test_rejeita_soc_inferior_a_reserva(self):
        with self.assertRaises(ValueError):
            SystemConfig(battery_soc_initial_pct=10, battery_soc_min_pct=20)

    def test_rejeita_identificador_duplicado(self):
        with self.assertRaises(ValueError):
            simulate_session([EVRequest("EV1"), EVRequest("EV1")], self.config)

    def test_bateria_nunca_ultrapassa_capacidade(self):
        battery = Bateria(capacidade_maxima=10, carga_inicial_percentual=90, reserva_minima_percentual=20)
        stored, _ = battery.carregar(100, 2)
        energy, soc = battery.status()
        self.assertLessEqual(energy, 10)
        self.assertLessEqual(soc, 100)
        self.assertGreaterEqual(stored, 0)

    def test_pedido_que_excede_intervalo_fica_pendente(self):
        result = simulate_session([EVRequest("EV1", 7, 12)], self.config, "PV + Battery")
        self.assertLessEqual(result["energia_entregue_kwh"], 7 + 1e-6)
        self.assertGreaterEqual(result["energia_nao_atendida_kwh"], 5 - 1e-6)

    def test_prioridade_ponderada_direciona_mais_potencia(self):
        cfg = SystemConfig(hour=0, station_limit_kw=4, grid_limit_kw=4, battery_soc_initial_pct=20)
        requests = [EVRequest("EV_prioritario", 7, 7, 2), EVRequest("EV_normal", 7, 7, 1)]
        result = simulate_session(requests, cfg, "PV Priority")
        priority_ev = next(row for row in result["veiculos"] if row["veiculo"] == "EV_prioritario")
        normal_ev = next(row for row in result["veiculos"] if row["veiculo"] == "EV_normal")
        self.assertGreater(priority_ev["potencia_atendida_kw"], normal_ev["potencia_atendida_kw"])

    def test_custo_total_e_soma_das_fontes(self):
        result = simulate_session(self.vehicles, self.config, "PV + Battery")
        self.assertAlmostEqual(
            result["custo_total_rs"],
            result["custo_solar_rs"] + result["custo_bateria_rs"] + result["custo_rede_rs"],
            places=2,
        )

    def test_execucao_e_reprodutivel(self):
        first = simulate_session(self.vehicles, self.config, "PV + Battery")
        second = simulate_session(self.vehicles, self.config, "PV + Battery")
        self.assertEqual(first, second)

    def test_custos_individuais_reconciliam_com_total(self):
        result = simulate_session(self.vehicles, self.config, "PV + Battery")
        self.assertAlmostEqual(sum(row["custo_rs"] for row in result["veiculos"]), result["custo_total_rs"], places=2)

    def test_config_rejeita_duracao_infinita(self):
        with self.assertRaises(ValueError):
            SystemConfig(duration_h=float("inf"))

    def test_assistente_explicita_uso_solar(self):
        result = simulate_session(self.vehicles, self.config, "PV + Battery")
        answer = responder_pergunta("Como foi usada a energia solar?", result)
        self.assertIn("12.75 kWh", answer)
        self.assertIn("não é leitura de sensor real", answer)

    def test_assistente_explica_custo_estimado(self):
        result = simulate_session(self.vehicles, self.config, "PV + Battery")
        answer = responder_pergunta("Quanto economizamos?", result)
        self.assertIn("R$ 6.35", answer)
        self.assertIn("não preços oficiais", answer)

    def test_assistente_compara_estrategias(self):
        comparisons = compare_modes(self.vehicles, self.config)
        result = next(row for row in comparisons if row["modo"] == "PV + Battery")
        answer = responder_pergunta("Compare os modos de carregamento", result, comparisons)
        self.assertIn("PV Priority", answer)
        self.assertIn("PV + Battery", answer)

    def test_assistente_responde_pergunta_vazia(self):
        result = simulate_session(self.vehicles, self.config, "PV + Battery")
        self.assertIn("Digite uma pergunta", responder_pergunta("   ", result))


if __name__ == "__main__":
    unittest.main(verbosity=2)
