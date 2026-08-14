"""
test_gemini_service.py - Suite de Pruebas Automatizadas para el Cliente Gemini y Yara AI
"""

import unittest
from services.gemini_service import (
    get_gemini_response,
    normalizar_texto_coloquial,
    YARA_SYSTEM_PROMPT
)
from state_manager import init_session_state, CLIENTES_CATALOGO
import streamlit as st


class TestGeminiService(unittest.TestCase):

    def setUp(self):
        st.session_state.clear()
        init_session_state()

    def test_normalizador_peruano(self):
        """Valida que el normalizador interprete jergas y abreviaturas peruanas."""
        frase = "mano xq m vino 80 lucas mas en el recibo si tenia promo"
        norm = normalizar_texto_coloquial(frase)
        self.assertIn("por qué", norm)
        self.assertIn("me", norm)
        self.assertIn("soles", norm)

    def test_consulta_coloquial_variacion_recibo(self):
        """Valida la consulta en jerga sobre por qué subió el recibo para CLI001."""
        client_ctx = CLIENTES_CATALOGO["CLI001"]
        prompt = "mano xq m vino 30 lucas mas en el recibo si tenia promo"
        
        res = get_gemini_response(
            chat_history=[],
            user_message=prompt,
            client_context=client_ctx
        )
        
        self.assertIn("response_text", res)
        self.assertIn("+S/ 30.00", res["response_text"])
        self.assertIn("repetidor", res["response_text"].lower())
        self.assertGreater(len(res["tool_calls_executed"]), 0)

    def test_consulta_coloquial_movistar_total(self):
        """Valida consulta en jerga solicitando ahorro con Movistar Total para 1000001."""
        client_ctx = CLIENTES_CATALOGO["1000001"]
        prompt = "habla causa como hago para unificar mi linea y ahorrar con movistar total"
        
        res = get_gemini_response(
            chat_history=[],
            user_message=prompt,
            client_context=client_ctx
        )
        
        self.assertIn("Movistar Total", res["response_text"])
        self.assertIn("Ahorro Real", res["response_text"])
        self.assertEqual(res["action_payload"]["action"], "SHOW_UPGRADE_CARD")

    def test_anti_alucinacion_estricta(self):
        """Valida que una consulta de dato no existente responda exactamente la directiva."""
        client_ctx = {"id": "CLI999", "nombre": "Desconocido"}
        prompt = "¿Cuál es el saldo de mi tarjeta de crédito Movistar Visa?"
        
        res = get_gemini_response(
            chat_history=[],
            user_message=prompt,
            client_context=client_ctx
        )
        
        self.assertIn("No encuentro ese registro en tu cuenta actual", res["response_text"])

    def test_escalamiento_coloquial_a_humano(self):
        """Valida escalamiento cuando el cliente solicita un operador humano."""
        client_ctx = CLIENTES_CATALOGO["CLI001"]
        prompt = "oe causa pasame con un asesor humano al toque"
        
        res = get_gemini_response(
            chat_history=[],
            user_message=prompt,
            client_context=client_ctx
        )
        
        self.assertIn("He transferido tu caso a uno de nuestros asesores especializados", res["response_text"])
        self.assertIn("TCK-", res["response_text"])
        self.assertEqual(res["action_payload"]["action"], "TRIGGER_ESCALATION")

    def test_system_prompt_maestro(self):
        """Valida que el System Prompt contenga las directivas de Yara AI y 0% alucinaciones."""
        self.assertIn("YARA AI", YARA_SYSTEM_PROMPT)
        self.assertIn("REGLA INFLEXIBLE DE CERO ALUCINACIONES", YARA_SYSTEM_PROMPT)
        self.assertIn("lucas", YARA_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
