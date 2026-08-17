"""
test_gemini_service.py - Suite de Pruebas Automatizadas para el Cliente Gemini y Yara AI
"""

import unittest
from services.gemini_service import (
    get_gemini_response,
    normalizar_texto_coloquial,
    clasificar_intencion_y_keys,
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

    def test_clasificador_intencion_scores(self):
        """Valida que el clasificador semántico identifique la intención de aumento de recibo."""
        res = clasificar_intencion_y_keys("oye puto poq me cobran de mas?")
        self.assertEqual(res["top_intent"], "BILLING_INCREASE")
        self.assertGreater(res["score"], 0.3)

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
        self.assertTrue("30" in res["response_text"] or "repetidor" in res["response_text"].lower())

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
        self.assertTrue(any(k in res["response_text"].lower() for k in ["ahorr", "s/"]))
        self.assertEqual(res["action_payload"]["action"], "SHOW_UPGRADE_CARD")


    def test_escalamiento_coloquial_a_humano(self):
        """Valida escalamiento cuando el cliente solicita un operador humano."""
        client_ctx = CLIENTES_CATALOGO["CLI001"]
        prompt = "oe causa pasame con un asesor humano al toque"
        
        res = get_gemini_response(
            chat_history=[],
            user_message=prompt,
            client_context=client_ctx
        )
        
        self.assertTrue("asesor" in res["response_text"].lower() or "TCK-" in res["response_text"])
        self.assertIn(res["action_payload"]["action"], ["TRIGGER_ESCALATION", "SHOW_ADVISOR_BUTTON"])


    def test_efecto_efervescente(self):
        """Valida que al agradecer/finalizar la conversación, la IA recuerde los beneficios activos del plan."""
        client_ctx = CLIENTES_CATALOGO["CLI001"]
        prompt = "Muchas gracias, ya entendí todo claro"
        res = get_gemini_response(
            chat_history=[
                {"role": "user", "content": "¿Por qué subió mi recibo?"},
                {"role": "assistant", "content": "Subió por el repetidor WiFi."}
            ],
            user_message=prompt,
            client_context=client_ctx
        )
        self.assertIn("response_text", res)
        # Debe contener tono de despedida y mención de beneficios o deseos positivos
        self.assertTrue(any(k in res["response_text"].lower() for k in ["placer", "gusto", "recuerda", "plan", "fibra", "excelente día", "de nada"]))

    def test_action_hub_en_variacion(self):
        """Valida que ante preguntas de variación de recibo, se retorne el payload del hub de acciones."""
        client_ctx = CLIENTES_CATALOGO["CLI001"]
        prompt = "¿Por qué me vino más caro este mes?"
        res = get_gemini_response(
            chat_history=[],
            user_message=prompt,
            client_context=client_ctx
        )
        self.assertIn("action_payload", res)
        self.assertIn(res["action_payload"]["action"], ["SHOW_ACTIONS_HUB", "SHOW_BILLING_BREAKDOWN"])

    def test_consulta_posibles_acciones(self):
        """Valida que cuando el cliente pregunta qué opciones o qué puede hacer, la IA le recomiende acciones."""
        client_ctx = CLIENTES_CATALOGO["CLI001"]
        prompt = "¿Qué opciones tengo o qué puedo hacer con este recibo?"
        res = get_gemini_response(
            chat_history=[],
            user_message=prompt,
            client_context=client_ctx
        )
        self.assertIn("action_payload", res)
        self.assertEqual(res["action_payload"]["action"], "SHOW_ACTIONS_HUB")
        self.assertTrue(any(k in res["response_text"].lower() for k in ["pago", "pagar", "fraccion", "cuotas", "consulta", "asesor", "opci", "recibo", "plan"]))

    def test_system_prompt_maestro(self):

        """Valida que el System Prompt contenga las directivas de Yara AI y 0% alucinaciones."""
        self.assertIn("YARA AI", YARA_SYSTEM_PROMPT)
        self.assertIn("0% ALUCINACIONES", YARA_SYSTEM_PROMPT)
        self.assertIn("lucas", YARA_SYSTEM_PROMPT)


if __name__ == "__main__":


    unittest.main()
