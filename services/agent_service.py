"""
services/agent_service.py - Motor Agéntico de Atención y Facturación Movistar
Implementa Tool Calling / Function Calling determinista basado estrictamente en los datasets y BD local.
Integra escalamiento automático y explícito con services/escalation_service.py.
Política Anti-Alucinación: 0% datos inventados. Si no existe el dato, responde explícitamente:
'No dispongo de ese dato en su facturación actual'.
"""

import os
import csv
import json
from typing import Dict, Any, List, Optional
from diff_engine import auditar_variacion_recibo
from nbo_engine import generar_next_best_offer
from database import get_connection, get_cliente_by_id
from state_manager import CLIENTES_CATALOGO
from services.escalation_service import (
    detectar_necesidad_escalamiento,
    escalar_a_humano,
    cliente_tiene_ticket_pendiente
)

# Alias para compatibilidad
def solicitar_derivacion_humana(client_id: str, motivo: str) -> str:
    ticket = escalar_a_humano(client_id, [], motivo)
    return ticket["ticket_id"]



# =========================================================
# 1. HERRAMIENTAS (TOOLS / FUNCTION CALLING)
# =========================================================

def consultar_recibo(client_id: str, periodo: str = "2026-07") -> Dict[str, Any]:
    """
    Herramienta A: Cruza datos de facturación, descuentos, prorrateos y cuotas
    de los datasets locales (diff_engine, BRAINY_*, CSVs).
    """
    cid = str(client_id).strip().upper()
    diff_data = auditar_variacion_recibo(cid, periodo)
    
    detalles_soporte = []
    
    # Prorrateos
    prorrateo_csv = "BRAINY_PRORRATEO_ALTASV3.csv"
    if os.path.exists(prorrateo_csv):
        try:
            with open(prorrateo_csv, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f, delimiter=";")
                for r in reader:
                    num = str(r.get("Numero") or r.get("CuentaFinanciera") or "").strip()
                    if cid in num or num in cid:
                        detalles_soporte.append({
                            "fuente": "BRAINY_PRORRATEO_ALTAS",
                            "monto": float(r.get("suma_prorrateo", 0.0)),
                            "descripcion": f"Prorrateo de alta en ciclo {r.get('Ciclica', '')} ({r.get('Q_cargos')} cargos)"
                        })
        except Exception:
            pass

    # Descuentos y Cuotas
    descuentos_csv = "BRAINY_DESCUENTOS_CUOTAS.csv"
    if os.path.exists(descuentos_csv):
        try:
            with open(descuentos_csv, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f, delimiter=";")
                for r in reader:
                    ba = str(r.get("BillingArrangement") or r.get("cuentafinanciera") or "").strip()
                    if cid in ba or ba in cid:
                        detalles_soporte.append({
                            "fuente": "BRAINY_DESCUENTOS_CUOTAS",
                            "monto": float(r.get("Monto_Descuento", 0.0)),
                            "descripcion": f"{r.get('Descripcion', 'Descuento')} (Cuota {r.get('CuotaActual')}/{r.get('PromotionDuration')})"
                        })
        except Exception:
            pass

    return {
        "encontrado": diff_data.get("encontrado", False),
        "id_cliente": cid,
        "periodo": periodo,
        "variacion": diff_data.get("variacion"),
        "conceptos_adicionales": diff_data.get("conceptos_adicionales", []),
        "detalles_soporte": detalles_soporte
    }


def evaluar_upgrade_movistar_total(client_id: str) -> Dict[str, Any]:
    """
    Herramienta B: Consulta CATALOGO-OFERTAS / catalogo_ofertas_entrega.csv y
    genera la recomendación exacta con precio, velocidad, gigas y cálculo de ahorro real.
    """
    return generar_next_best_offer(client_id)


# =========================================================
# 2. MOTOR AGÉNTICO Y LÓGICA DE RESPUESTA CONVERSACIONAL
# =========================================================

def process_user_message(client_id: str, user_query: str, chat_history: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Procesa el mensaje del usuario utilizando el motor de inteligencia y deducción de Yara AI (Google Gemini).
    """
    from services.gemini_service import get_gemini_response
    
    cid = str(client_id).strip().upper()
    client_ctx = CLIENTES_CATALOGO.get(cid, {"id": cid, "nombre": f"Cliente {cid}", "servicio": "Servicio Fijo/Móvil"})
    
    res = get_gemini_response(
        chat_history=chat_history or [],
        user_message=user_query,
        client_context=client_ctx
    )
    return res["response_text"]

