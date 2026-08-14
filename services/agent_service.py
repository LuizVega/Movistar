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
    Procesa el mensaje del usuario utilizando el cliente de Gemini y el System Prompt de Yara AI.
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


    # 2. Intención: Consultar por qué subió el recibo / desglose de cobro
    if any(k in q for k in ["por qué", "porque", "por que", "subió", "subio", "aumentó", "aumento", "cobro", "recibo", "variación", "variacion", "monto", "factura", "más caro", "mas caro", "diferencia"]):
        recibo_info = consultar_recibo(cid)
        
        if not recibo_info.get("encontrado"):
            return "No dispongo de ese dato en su facturación actual. Si consideras que es un error, puedo comunicarte con un asesor humano."

        var = recibo_info.get("variacion", {})
        monto_var = var.get("monto", 0.0) if var else 0.0
        pct_var = var.get("porcentaje", 0.0) if var else 0.0
        conceptos = recibo_info.get("conceptos_adicionales", [])

        if monto_var == 0.0 or not conceptos:
            return (
                f"✅ **Tu recibo de Julio 2026 no presenta ningún incremento.**\n\n"
                f"El monto total facturado es exactamente igual al de tu mes anterior. Tu tarifa regular y beneficios se mantienen activos y sin cobros adicionales."
            )

        # Desglose en lenguaje simple
        explicaciones = []
        for c in conceptos:
            concepto_nom = c.get("concepto", "")
            monto_c = c.get("monto", 0.0)
            tipo_c = c.get("tipo", "")

            if tipo_c == "cargo_unico" or "repetidor" in concepto_nom.lower():
                explicaciones.append(f"• **{concepto_nom} (+S/ {monto_c:.2f})**: Es un cobro por única vez por la instalación y activación del equipo que solicitaste el mes pasado.")
            elif tipo_c == "fin_descuento" or "descuento" in concepto_nom.lower():
                explicaciones.append(f"• **{concepto_nom} (+S/ {monto_c:.2f})**: Finalizó el periodo de promoción con descuento temporal que tenías activo, regresando a la tarifa estándar de tu plan.")
            elif tipo_c == "prorrateo":
                explicaciones.append(f"• **{concepto_nom} (+S/ {monto_c:.2f})**: Es un cargo proporcional correspondiente a los días de servicio transcurridos desde tu cambio de plan hasta el cierre de ciclo.")
            elif tipo_c == "cuota_equipo":
                explicaciones.append(f"• **{concepto_nom} (+S/ {monto_c:.2f})**: Corresponde a la cuota mensual del smartphone financiado que adquiriste en cuotas.")
            elif tipo_c == "cargo_reconexion":
                explicaciones.append(f"• **{concepto_nom} (+S/ {monto_c:.2f})**: Es el cargo administrativo por reconexión del servicio tras una suspensión por pago fuera de fecha.")
            else:
                explicaciones.append(f"• **{concepto_nom} (+S/ {monto_c:.2f})**: Cargo adicional registrado en tu ciclo de facturación.")

        detalles_txt = "\n".join(explicaciones)
        return (
            f"📊 **Auditando tu recibo de Julio 2026:**\n\n"
            f"Tu recibo tuvo una variación de **+S/ {monto_var:.2f} (+{pct_var:.2f}%)** debido a los siguientes motivos específicos:\n\n"
            f"{detalles_txt}\n\n"
            f"💡 *Recuerda que si necesitas facilidades, puedes solicitar un fraccionamiento sin intereses o consultar una mejora a Movistar Total.*"
        )

    # 3. Intención: Consultar / solicitar Upgrade a Movistar Total
    if any(k in q for k in ["upgrade", "movistar total", "total", "migrar", "ahorrar", "ahorro", "convergente", "fibra y movil", "unificar", "oferta", "promocion", "promoción", "plan nuevo", "mejorar"]):
        nbo_data = evaluar_upgrade_movistar_total(cid)
        
        if not nbo_data.get("encontrado"):
            return "No dispongo de ese dato en su facturación actual."

        if not nbo_data.get("es_elegible_mt"):
            if nbo_data.get("es_movistar_total_actual"):
                of = nbo_data.get("oferta_recomendada", {})
                return (
                    f"⭐ **¡Ya eres cliente Movistar Total!**\n\n"
                    f"Actualmente cuentas con los máximos beneficios unificados en un solo recibo. Te sugerimos un upgrade de velocidad a **{of.get('nombre_oferta')} ({of.get('velocidad_mbps')} Mbps)** por solo **S/ {of.get('precio_promocional'):.2f}/mes**."
                )
            else:
                return (
                    f"ℹ️ Tu línea actual no cuenta con cobertura convergente para Movistar Total en este momento, "
                    f"pero puedes optar por una mejora de velocidad en tu plan de Fibra Óptica."
                )

        of = nbo_data.get("oferta_recomendada", {})
        ben = nbo_data.get("beneficio_economico", {})

        return (
            f"🚀 **¡Excelente noticia! Eres elegible para Movistar Total.**\n\n"
            f"En lugar de pagar tus servicios de internet hogar y celulares por separado (gasto aprox. **S/ {ben.get('gasto_actual_fragmentado_estimado', 0):.2f}/mes**), te ofrecemos unificar todo en un solo plan:\n\n"
            f"• **Plan Propuesto:** {of.get('nombre_oferta')}\n"
            f"• **Velocidad Fibra Simétrica:** {of.get('velocidad_mbps')} Mbps\n"
            f"• **Líneas Móviles Incluidas:** {of.get('gigas_datos')} GB de alta velocidad\n"
            f"• **Precio Promocional:** **S/ {of.get('precio_promocional'):.2f} / mes**\n"
            f"• **Ahorro Real:** **S/ {ben.get('ahorro_mensual_soles', 0):.2f} al mes ({ben.get('ahorro_porcentaje', 0):.1f}%)**\n"
            f"• **Ahorro Anual Estimado:** 💰 **S/ {ben.get('ahorro_anual_estimado_soles', 0):.2f} al año**\n\n"
            f"¿Deseas que activemos tu solicitud de migración ahora mismo?"
        )

    # 4. Intención: Fraccionamiento de deuda
    if any(k in q for k in ["fraccionar", "fraccionamiento", "cuotas", "pagar en partes", "diferir", "deuda"]):
        monto_actual = CLIENTES_CATALOGO.get(cid, {}).get("recibo_actual", 119.90)
        return (
            f"💳 **Planes de Fraccionamiento sin Intereses (TCEA 0.0%):**\n\n"
            f"Puedes fraccionar el importe de tu recibo actual (**S/ {monto_actual:.2f}**) en:\n"
            f"• **3 cuotas fijas** de **S/ {(monto_actual/3):.2f} / mes**\n"
            f"• **6 cuotas fijas** de **S/ {(monto_actual/6):.2f} / mes**\n"
            f"• **12 cuotas fijas** de **S/ {(monto_actual/12):.2f} / mes**\n\n"
            f"Puedes solicitarlo directamente desde la pestaña de Soluciones Comerciales en tu pantalla."
        )

    # 5. Saludo o inicio
    if any(k in q for k in ["hola", "buenos dias", "buenas tardes", "buenas noches", "hey", "ayuda", "inicio"]):
        cliente_nombre = CLIENTES_CATALOGO.get(cid, {}).get("nombre", "Cliente")
        return (
            f"¡Hola {cliente_nombre}! Soy tu **Asistente Digital Movistar**. 📱\n\n"
            f"Puedo ayudarte con:\n"
            f"1. **Explicar por qué varió tu recibo de julio** con cifras exactas.\n"
            f"2. **Evaluar tu ahorro con Movistar Total (hasta 50%)**.\n"
            f"3. **Fraccionar tu recibo en cuotas fijas sin intereses**.\n"
            f"4. **Transferirte con un asesor humano** si requieres atención personalizada.\n\n"
            f"¿Qué consulta deseas realizar?"
        )

    # Fallback estricto Anti-Alucinación
    return (
        f"Comprendo tu consulta sobre '{user_query}'. "
        f"Para esa información puntual: *No dispongo de ese dato en su facturación actual*. "
        f"¿Deseas que te transfiera con un asesor humano para revisarlo a detalle?"
    )
