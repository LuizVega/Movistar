"""
test_chat_elements.py - Suite de Pruebas Unitarias para Componentes Interactivos de Chat
"""

import unittest
from components.chat_elements import render_chat_action_elements
from state_manager import init_session_state, CLIENTES_CATALOGO
import streamlit as st


class TestChatElements(unittest.TestCase):

    def setUp(self):
        st.session_state.clear()
        init_session_state()

    def test_render_upgrade_action_detection(self):
        """Valida la detección de acción de upgrade a Movistar Total."""
        msg = {
            "role": "assistant",
            "content": "Te sugiero migrar a Movistar Total con 50% de ahorro.",
            "metadata": {
                "action_payload": {
                    "action": "SHOW_UPGRADE_CARD",
                    "nbo": {
                        "es_elegible_mt": True,
                        "oferta_recomendada": {
                            "nombre_oferta": "Movistar Total Dúo 200 Mbps + 1 Línea",
                            "precio_promocional": 110.40,
                            "velocidad_mbps": 200,
                            "gigas_datos": 40
                        },
                        "beneficio_economico": {
                            "ahorro_mensual_soles": 29.40,
                            "ahorro_porcentaje": 21.0,
                            "ahorro_anual_estimado_soles": 352.80
                        }
                    }
                }
            }
        }
        
        # Ejecutar render (en modo test)
        try:
            render_chat_action_elements(msg, 1, CLIENTES_CATALOGO["1000001"])
            success = True
        except Exception as e:
            success = False
            
        self.assertTrue(success)

    def test_render_fraccionamiento_action_detection(self):
        """Valida la detección de acción de fraccionamiento de deuda."""
        msg = {
            "role": "assistant",
            "content": "Puedes fraccionar tu recibo en cuotas fijas sin intereses.",
            "metadata": {
                "action_payload": {
                    "action": "SHOW_INSTALLMENT_MODAL",
                    "monto": 119.90
                }
            }
        }
        
        try:
            render_chat_action_elements(msg, 2, CLIENTES_CATALOGO["CLI001"])
            success = True
        except Exception as e:
            success = False

        self.assertTrue(success)


if __name__ == "__main__":
    unittest.main()
