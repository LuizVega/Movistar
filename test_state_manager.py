"""
test_state_manager.py - Suite de Pruebas Automatizadas para Gestor de Estado y Roles
"""

import unittest
from state_manager import (
    init_session_state,
    add_chat_message,
    escalate_case_to_human,
    update_ticket_status,
    get_active_client_data,
    CLIENTES_CATALOGO
)
import streamlit as st


class TestStateManager(unittest.TestCase):

    def setUp(self):
        # Limpiar y re-inicializar el estado de sesión
        st.session_state.clear()
        init_session_state()

    def test_initial_state(self):
        """Verifica que todas las variables requeridas existan con tipos correctos."""
        self.assertEqual(st.session_state.user_role, "cliente")
        self.assertIsInstance(st.session_state.chat_history, list)
        self.assertIsInstance(st.session_state.escalated_tickets, list)
        self.assertGreater(len(st.session_state.escalated_tickets), 0)


    def test_escalate_ticket(self):
        """Valida la creación y esquema de un ticket escalado."""
        initial_count = len(st.session_state.escalated_tickets)
        t_id = escalate_case_to_human("CLI001", "Juan Pérez", "Reclamo por cobro de repetidor")
        
        self.assertTrue(t_id.startswith("TCK-"))
        self.assertEqual(len(st.session_state.escalated_tickets), initial_count + 1)
        
        ticket = st.session_state.escalated_tickets[0]
        self.assertEqual(ticket["ticket_id"], t_id)
        self.assertEqual(ticket["client_id"], "CLI001")
        self.assertEqual(ticket["status"], "PENDIENTE")
        self.assertEqual(ticket["priority"], "ALTA")
        self.assertIsInstance(ticket["chat_history"], list)

    def test_update_ticket(self):
        """Valida la actualización de estado y notas de un ticket."""
        t_id = escalate_case_to_human("CLI002", "María Torres", "Consulta de descuento")
        update_ticket_status(t_id, "EN_ATENCION", notes="Asesor asignado revisando", agent="Carlos Vega")
        
        ticket = next(t for t in st.session_state.escalated_tickets if t["ticket_id"] == t_id)
        self.assertEqual(ticket["status"], "EN_ATENCION")
        self.assertEqual(ticket["notes"], "Asesor asignado revisando")
        self.assertEqual(ticket["assigned_agent"], "Carlos Vega")

    def test_add_chat_message(self):
        """Valida el registro de mensajes de chat en la sesión."""
        initial_msgs = len(st.session_state.chat_history)
        add_chat_message("user", "¿Cuánto debo pagar en julio?")
        self.assertEqual(len(st.session_state.chat_history), initial_msgs + 1)
        self.assertEqual(st.session_state.chat_history[-1]["content"], "¿Cuánto debo pagar en julio?")

    def test_role_switch_preserves_state(self):
        """Valida que cambiar de rol conserve los tickets y el historial intactos."""
        t_id = escalate_case_to_human("CLI005", "Roberto Díaz", "Equipo financiado")
        add_chat_message("user", "Pregunta de prueba cliente")
        
        # Cambiar a modo trabajador
        st.session_state.user_role = "trabajador"
        self.assertEqual(st.session_state.user_role, "trabajador")
        
        # Verificar que los tickets e historial siguen existiendo
        self.assertTrue(any(t["ticket_id"] == t_id for t in st.session_state.escalated_tickets))
        self.assertTrue(any(m["content"] == "Pregunta de prueba cliente" for m in st.session_state.chat_history))
        
        # Volver a modo cliente
        st.session_state.user_role = "cliente"
        self.assertEqual(st.session_state.user_role, "cliente")
        self.assertTrue(any(t["ticket_id"] == t_id for t in st.session_state.escalated_tickets))


if __name__ == "__main__":
    unittest.main()
