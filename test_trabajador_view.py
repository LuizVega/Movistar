"""
test_trabajador_view.py - Pruebas Unitarias para la Vista del Trabajador / Asesor CRM
"""

import unittest
from database import get_ficha_cliente_completa, get_cliente_by_id
from state_manager import (
    init_session_state,
    update_ticket_status,
    add_chat_message
)
from services.escalation_service import escalar_a_humano
import streamlit as st


class TestTrabajadorView(unittest.TestCase):

    def setUp(self):
        st.session_state.clear()
        init_session_state()

    def test_get_ficha_cliente_completa(self):
        """Valida que la función agregue datos de SQLite y CSVs."""
        ficha = get_ficha_cliente_completa("1000001")
        self.assertEqual(ficha["cliente_id"], "1000001")
        self.assertIsNotNone(ficha["datos_bd"])
        self.assertIsInstance(ficha["descuentos_activos"], list)
        self.assertIsInstance(ficha["prorrateos_registrados"], list)
        self.assertTrue("elegible_mt" in ficha)

    def test_workflow_atencion_asesor(self):
        """Valida el ciclo completo de escalamiento, inspección, notas y resolución por asesor."""
        # 1. Escalar caso
        ticket = escalar_a_humano(
            client_id="CLI001",
            chat_history=[{"role": "user", "content": "Tengo un reclamo"}],
            motivo_detectado="Reclamo de repetidor WiFi",
            prioridad="ALTA"
        )
        t_id = ticket["ticket_id"]
        self.assertEqual(ticket["status"], "PENDIENTE")

        # 2. Pasar a EN_ATENCION
        update_ticket_status(t_id, "EN_ATENCION", notes="Asesor revisando cuenta", agent="Carlos Vega")
        t_actual = next(t for t in st.session_state.escalated_tickets if t["ticket_id"] == t_id)
        self.assertEqual(t_actual["status"], "EN_ATENCION")
        self.assertEqual(t_actual["assigned_agent"], "Carlos Vega")

        # 3. Enviar mensaje del asesor al chat
        add_chat_message("assistant", "👔 Asesor Carlos Vega: Hola Juan, he revisado tu caso.")
        self.assertTrue(any("Asesor Carlos Vega" in m["content"] for m in st.session_state.chat_history))

        # 4. Marcar como RESUELTO
        update_ticket_status(t_id, "RESUELTO", notes="Cobro de repetidor exonerado por fidelización")
        t_resuelto = next(t for t in st.session_state.escalated_tickets if t["ticket_id"] == t_id)
        self.assertEqual(t_resuelto["status"], "RESUELTO")


if __name__ == "__main__":
    unittest.main()
