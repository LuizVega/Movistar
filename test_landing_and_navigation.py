"""
test_landing_and_navigation.py - Pruebas Unitarias del Flujo de Navegacion y Vistas
"""

import unittest
from state_manager import init_session_state, reset_chat, CLIENTES_CATALOGO
from views.landing_view import render_landing_view
from views.cliente_view import render_cliente_view
from views.trabajador_view import render_trabajador_view
import streamlit as st


class TestLandingAndNavigation(unittest.TestCase):

    def setUp(self):
        st.session_state.clear()
        init_session_state()

    def test_initial_view_mode_is_landing(self):
        """Valida que la vista inicial por defecto sea 'landing'."""
        self.assertEqual(st.session_state.view_mode, "landing")

    def test_reset_chat(self):
        """Valida que reset_chat() reinicie el historial al saludo oficial."""
        st.session_state.chat_history.append({"role": "user", "content": "mensaje de prueba"})
        self.assertGreater(len(st.session_state.chat_history), 1)
        
        reset_chat()
        self.assertEqual(len(st.session_state.chat_history), 1)
        self.assertEqual(st.session_state.chat_history[0]["role"], "assistant")
        self.assertIn("Yara AI", st.session_state.chat_history[0]["content"])

    def test_render_views_without_exceptions(self):
        """Valida que las 3 vistas rendericen limpiamente en modo bare."""
        try:
            render_landing_view()
            st.session_state.view_mode = "cliente"
            render_cliente_view()
            st.session_state.view_mode = "trabajador"
            render_trabajador_view()
            success = True
        except Exception as e:
            success = False
            print(f"Error en render: {e}")

        self.assertTrue(success)


if __name__ == "__main__":
    unittest.main()
