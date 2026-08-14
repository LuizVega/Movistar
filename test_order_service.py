"""
test_order_service.py - Suite de Pruebas Unitarias para el Servicio de Órdenes y Transacciones (Yara AI)
"""

import unittest
import os
import csv
from services.order_service import (
    ejecutar_upgrade_plan,
    ejecutar_fraccionamiento_deuda,
    consultar_ordenes_cliente,
    calcular_fechas_ciclo
)
from state_manager import init_session_state, CLIENTES_CATALOGO
import streamlit as st


class TestOrderService(unittest.TestCase):

    def setUp(self):
        st.session_state.clear()
        init_session_state()

    def test_calcular_fechas_ciclo(self):
        """Valida que se calculen correctamente las fechas de corte y vigencia."""
        fechas = calcular_fechas_ciclo()
        self.assertIn("fecha_registro", fechas)
        self.assertIn("fecha_corte", fechas)
        self.assertIn("fecha_vigencia", fechas)
        self.assertTrue(fechas["fecha_corte"].endswith("-28"))
        self.assertTrue(fechas["fecha_vigencia"].endswith("-01"))

    def test_ejecutar_upgrade_plan_exitoso(self):
        """Valida la ejecución formal del upgrade a Movistar Total."""
        cid = "1000001"
        res = ejecutar_upgrade_plan(cliente_id=cid, canal="YARA_AI")
        
        self.assertTrue(res["exito"])
        self.assertTrue(res["orden_id"].startswith("ORD-"))
        self.assertEqual(res["cliente_id"], cid)
        self.assertIn("Movistar Total", res["nuevo_plan"])
        self.assertGreater(res["precio_nuevo"], 0.0)
        self.assertGreater(res["ahorro_mensual"], 0.0)
        
        # Mensaje de Yara AI con formato de comprobante
        self.assertIn("¡Listo! He procesado tu solicitud con éxito", res["mensaje_yara"])
        self.assertIn(res["orden_id"], res["mensaje_yara"])
        self.assertIn("Movistar Total", res["mensaje_yara"])
        
        # Validación de actualización en memoria
        self.assertIn("Movistar Total", CLIENTES_CATALOGO[cid]["servicio"])

        # Validación en SQLite
        ordenes_db = consultar_ordenes_cliente(cid)
        self.assertTrue(any(o["orden_id"] == res["orden_id"] for o in ordenes_db))

        # Validación en Ordenes.csv
        self.assertTrue(os.path.exists("Ordenes.csv"))

    def test_ejecutar_fraccionamiento_deuda(self):
        """Valida el registro de fraccionamiento de deuda sin intereses."""
        cid = "CLI001"
        monto = 120.00
        cuotas = 6
        res = ejecutar_fraccionamiento_deuda(cliente_id=cid, cuotas=cuotas, monto_total=monto)
        
        self.assertTrue(res["exito"])
        self.assertTrue(res["orden_id"].startswith("FRACC-"))
        self.assertEqual(res["cuotas"], 6)
        self.assertEqual(res["monto_cuota"], 20.00)
        self.assertIn("¡Listo! He procesado tu solicitud de fraccionamiento con éxito", res["mensaje_yara"])
        
        # Validación en SQLite
        ordenes_db = consultar_ordenes_cliente(cid)
        self.assertTrue(any(o["orden_id"] == res["orden_id"] for o in ordenes_db))


if __name__ == "__main__":
    unittest.main()
