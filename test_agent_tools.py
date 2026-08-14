"""
test_agent_tools.py - Suite de Pruebas Automatizadas para Tools de Gemini (Yara AI)
"""

import unittest
from services.agent_tools import (
    tool_consultar_detalle_recibo,
    tool_evaluar_upgrade_movistar_total,
    tool_verificar_reconexiones_notas,
    GEMINI_CALLABLE_TOOLS
)


class TestAgentTools(unittest.TestCase):

    def test_tool_consultar_detalle_recibo_cli001(self):
        """Valida que tool_consultar_detalle_recibo retorne cifras exactas y tipos nativos."""
        data = tool_consultar_detalle_recibo("CLI001")
        self.assertTrue(data["encontrado"])
        self.assertEqual(data["cliente_id"], "CLI001")
        self.assertEqual(data["monto_total_facturado"], 119.90)
        self.assertEqual(data["monto_anterior"], 89.90)
        self.assertEqual(data["variacion_monto"], 30.00)
        self.assertAlmostEqual(data["variacion_porcentaje"], 33.37, places=1)
        self.assertIsInstance(data["cargos_prorrateo"], list)
        self.assertIsInstance(data["descuentos_activos"], list)
        self.assertIn("Instalación de repetidor", data["motivo_principal"])

    def test_tool_evaluar_upgrade_movistar_total_1000001(self):
        """Valida que tool_evaluar_upgrade_movistar_total genere la recomendación convergente y payload."""
        data = tool_evaluar_upgrade_movistar_total("1000001")
        self.assertTrue(data["encontrado"])
        self.assertTrue(data["es_elegible_mt"])
        self.assertIn("Movistar Total", data["plan_recomendado"]["nombre_oferta"])
        self.assertEqual(data["plan_recomendado"]["precio_promocional"], 110.40)
        self.assertEqual(data["beneficio_economico"]["ahorro_mensual_soles"], 29.40)
        self.assertEqual(data["payload_confirmacion"]["accion"], "CONFIRMAR_UPGRADE_MOVISTAR_TOTAL")
        self.assertEqual(data["payload_confirmacion"]["cliente_id"], "1000001")

    def test_tool_verificar_reconexiones_notas(self):
        """Valida consulta de reconexiones y notas de crédito con tipos nativos."""
        data = tool_verificar_reconexiones_notas("CLI006")
        self.assertTrue(data["encontrado"])
        self.assertIsInstance(data["cargos_reconexion"], list)
        self.assertIsInstance(data["notas_credito"], list)
        self.assertIsInstance(data["suma_reconexiones"], float)
        self.assertIsInstance(data["saldo_a_favor"], float)

    def test_tool_cliente_no_existente(self):
        """Valida manejo limpio de errores para cliente inexistente."""
        data = tool_consultar_detalle_recibo("CLI999999")
        self.assertFalse(data["encontrado"])
        self.assertIn("No encuentro ese registro", data["error"])

    def test_gemini_callable_tools_registration(self):
        """Valida que las tools estén registradas y tengan docstrings para Function Calling."""
        self.assertEqual(len(GEMINI_CALLABLE_TOOLS), 3)
        for tool in GEMINI_CALLABLE_TOOLS:
            self.assertTrue(callable(tool))
            self.assertIsNotNone(tool.__doc__)


if __name__ == "__main__":
    unittest.main()
