"""
test_escalation_service.py - Pruebas Unitarias para el Servicio de Escalamiento Automático y Explícito
"""

import unittest
from services.escalation_service import (
    detectar_necesidad_escalamiento,
    escalar_a_humano,
    cliente_tiene_ticket_pendiente,
    generar_resumen_problema
)
from services.agent_service import process_user_message
from state_manager import init_session_state
import streamlit as st


class TestEscalationService(unittest.TestCase):

    def setUp(self):
        st.session_state.clear()
        init_session_state()

    def test_disparador_explicito(self):
        """Valida que frases explícitas activen el escalamiento."""
        frases = [
            "comunicarme con un asesor",
            "quiero hablar con una persona",
            "pásame con un operador",
            "necesito atención humana"
        ]
        for f in frases:
            debe, tipo, motivo = detectar_necesidad_escalamiento(f, [], "CLI001")
            self.assertTrue(debe, f"Falló para frase: {f}")
            self.assertEqual(tipo, "EXPLÍCITO")

    def test_disparador_automatico_baja_reclamo_grave(self):
        """Valida que solicitudes de baja o menciones a Indecopi/Osiptel escalen automáticamente."""
        frases = [
            "quiero dar de baja mi servicio",
            "voy a denunciar ante indecopi por estafa",
            "cancelar contrato de internet inmediatamente"
        ]
        for f in frases:
            debe, tipo, motivo = detectar_necesidad_escalamiento(f, [], "CLI001")
            self.assertTrue(debe, f"Falló para frase crítica: {f}")
            self.assertEqual(tipo, "AUTOMÁTICO_GRAVE")

    def test_disparador_automatico_frustracion(self):
        """Valida que señales de frustración activen escalamiento automático."""
        debe, tipo, motivo = detectar_necesidad_escalamiento("no me ayudas en nada, sigues sin responder", [], "CLI001")
        self.assertTrue(debe)
        self.assertEqual(tipo, "AUTOMÁTICO_FRUSTRACION")

    def test_creacion_ticket_esquema_completo(self):
        """Valida que escalar_a_humano inserte un ticket con resumen de 2-3 líneas y estado PENDIENTE."""
        historial_mock = [
            {"role": "user", "content": "¿Por qué mi recibo es tan alto?"},
            {"role": "assistant", "content": "Se debe a un cobro de repetidor."},
            {"role": "user", "content": "No estoy de acuerdo con ese cobro."}
        ]
        
        ticket = escalar_a_humano("CLI001", historial_mock, "Disconformidad con cobro de repetidor", "ALTA")
        
        self.assertTrue(ticket["ticket_id"].startswith("TCK-"))
        self.assertEqual(ticket["status"], "PENDIENTE")
        self.assertEqual(ticket["priority"], "ALTA")
        self.assertEqual(ticket["client_id"], "CLI001")
        self.assertEqual(len(ticket["chat_history"]), 3)
        self.assertIn("1. Motivo Principal:", ticket["summary"])
        self.assertIn("2. Contexto de Interacción:", ticket["summary"])
        self.assertIn("3. Acción Requerida:", ticket["summary"])
        
        # Verificar en sesión
        self.assertIsNotNone(cliente_tiene_ticket_pendiente("CLI001"))

    def test_respuesta_amable_notificacion_chat(self):
        """Valida que el bot responda con el mensaje estándar y el número de ticket."""
        historial = [{"role": "user", "content": "comunicarme con un asesor"}]
        respuesta = process_user_message("CLI001", "comunicarme con un asesor", historial)
        
        self.assertIn("He transferido tu caso a uno de nuestros asesores especializados", respuesta)
        self.assertIn("Ticket de Atención Asignado", respuesta)
        self.assertIn("TCK-", respuesta)


if __name__ == "__main__":
    unittest.main()
