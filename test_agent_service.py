"""
test_agent_service.py - Suite de Pruebas Unitarias para el Motor Agéntico y Tool Calling
"""

import unittest
from services.agent_service import (
    consultar_recibo,
    evaluar_upgrade_movistar_total,
    solicitar_derivacion_humana,
    process_user_message
)
from state_manager import init_session_state
import streamlit as st


class TestAgentService(unittest.TestCase):

    def setUp(self):
        st.session_state.clear()
        init_session_state()

    def test_consultar_recibo_cli001(self):
        """Valida que consultar_recibo descomponga exactamente el cargo del repetidor WiFi."""
        data = consultar_recibo("CLI001", "2026-07")
        self.assertTrue(data["encontrado"])
        self.assertEqual(data["id_cliente"], "CLI001")
        self.assertEqual(data["variacion"]["monto"], 30.00)
        self.assertEqual(data["variacion"]["porcentaje"], 33.37)
        self.assertEqual(len(data["conceptos_adicionales"]), 1)
        self.assertEqual(data["conceptos_adicionales"][0]["concepto"], "Instalación de repetidor WiFi")

    def test_evaluar_upgrade_movistar_total_1000001(self):
        """Valida que evaluar_upgrade_movistar_total genere la recomendación convergente con ahorro."""
        nbo = evaluar_upgrade_movistar_total("1000001")
        self.assertTrue(nbo["encontrado"])
        self.assertTrue(nbo["es_elegible_mt"])
        self.assertEqual(nbo["oferta_recomendada"]["tipo_oferta"], "MOVISTAR_TOTAL")
        self.assertGreater(nbo["beneficio_economico"]["ahorro_mensual_soles"], 0.0)

    def test_anti_hallucination_rule(self):
        """Valida que para datos no existentes responda estrictamente 'No dispongo de ese dato en su facturación actual'."""
        reply = process_user_message("CLI999", "¿Cuál es mi saldo?")
        self.assertIn("No dispongo de ese dato en su facturación actual", reply)

    def test_process_message_por_que_subio(self):
        """Valida respuesta agéntica a la pregunta de por qué subió el recibo."""
        reply = process_user_message("CLI001", "¿Por qué subió mi recibo este mes?")
        self.assertIn("+S/ 30.00", reply)
        self.assertIn("Instalación de repetidor WiFi", reply)

    def test_process_message_upgrade(self):
        """Valida respuesta agéntica a solicitud de Movistar Total."""
        reply = process_user_message("1000001", "Quiero saber cuánto puedo ahorrar con Movistar Total")
        self.assertIn("Movistar Total", reply)
        self.assertIn("Ahorro Real", reply)

    def test_process_message_escalar_humano(self):
        """Valida transferencia a asesor humano y generación de ticket."""
        reply = process_user_message("CLI001", "Deseo hablar con un asesor humano para hacer un reclamo")
        self.assertIn("TCK-", reply)
        self.assertIn("asesor humano", reply.lower())
        self.assertTrue(len(st.session_state.escalated_tickets) > 0)


if __name__ == "__main__":
    unittest.main()
