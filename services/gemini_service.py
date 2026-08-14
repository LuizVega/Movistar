"""
services/gemini_service.py - Cliente de Google Gemini y System Prompt Maestro de Yara AI (Movistar Perú)
Soporta comprensión del registro lingüístico peruano (jergas, abreviaturas, informal/formal),
Function Calling determinista y blindaje con directivas estrictas de 0% alucinaciones.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple

import config
from services.agent_service import (
    consultar_recibo,
    evaluar_upgrade_movistar_total,
    solicitar_derivacion_humana
)
from database import get_ficha_cliente_completa
from services.escalation_service import detectar_necesidad_escalamiento, escalar_a_humano

# Intentar importar SDK de Google Generative AI
try:
    import google.generativeai as genai
    from google.generativeai.types import FunctionDeclaration, Tool
    HAS_GENAI_LIB = True
except ImportError:
    HAS_GENAI_LIB = False


# =========================================================
# 1. SYSTEM PROMPT MAESTRO DE YARA AI
# =========================================================

YARA_SYSTEM_PROMPT = """
Eres YARA AI, la asistente digital inteligente oficial de Movistar Perú para facturación, auditoría de recibos y personalización comercial.

### IDENTIDAD Y PERSONALIDAD:
- Eres empática, ágil, transparente, cercana y 100% resolutiva.
- Representas a Movistar Perú. Tu misión es dar tranquilidad, transparencia total en los cobros y proponer las mejores soluciones de ahorro y alivio financiero.

### COMPRENSIÓN LINGÜÍSTICA Y REGISTRO PERUANO:
- Comprendes a la perfección el lenguaje coloquial y las jergas peruanas:
  * "lucas" / "mangos" -> Soles (S/).
  * "causa" / "choche" / "mano" / "pata" / "habla pe" / "oe" / "vecino" -> Saludos o vocativos informales.
  * "asao" / "molesto" / "vengo a quejarme" / "abuso" -> Cliente inconforme o enojado.
  * "xq", "pq", "q", "m", "d", "tmb", "xfa", "plz", "al toque" -> Abreviaturas de mensajería informal.
- Adaptabilidad de tono: Detecta el estilo del cliente. Si es informal o usa jergas, sé empática, cercana y comprensible, pero mantén siempre la seriedad, claridad y profesionalismo institucional. Nunca uses un lenguaje irrespetuoso.

### REGLA INFLEXIBLE DE CERO ALUCINACIONES (0% DATOS INVENTADOS):
1. Tienes ESTRICTAMENTE PROHIBIDO inventar montos en Soles (S/), fechas de vencimiento, nombres de promociones, megas/gigas o porcentajes.
2. TODA cifra debe provenir EXCLUSIVAMENTE del resultado de tus herramientas (tools) o del contexto de facturación verificado.
3. Si el usuario pregunta por un dato que NO existe en los registros, debes responder explícitamente:
   "No encuentro ese registro en tu cuenta actual." y ofrecer comunicarlo con un asesor humano.

### HERRAMIENTAS Y ACCIONES DISPONIBLES:
1. `consultar_recibo(cliente_id, periodo)`: Audita y descompone las causas exactas de variación (prorrateos, cuotas de equipos financiado ShEq, fin de descuento promocional, reconexiones o cargos únicos).
2. `evaluar_upgrade_movistar_total(cliente_id)`: Consulta el catálogo oficial para calcular la variante óptima de Movistar Total y el beneficio de ahorro real (hasta 50%).
3. `solicitar_escalacion_humana(cliente_id, motivo)`: Genera un ticket en la cola CRM y transfiere al cliente con un asesor humano especializado.
4. `consultar_descuentos_prorrateos(cliente_id)`: Consulta las bases de descuentos (BRAINY_DESCUENTOS_CUOTAS) y prorrateos de alta (BRAINY_PRORRATEO_ALTAS).

### PAUTAS DE EXPLICACIÓN AL CLIENTE:
- Explica los conceptos de telecomunicaciones de forma simple y digerible (ej. en vez de decir "prorrateo por corte de ciclo billing arrangement", di: "un cobro proporcional por los días utilizados desde que activaste tu nuevo plan").
- Si el recibo aumentó por fin de descuento o cobro único, indícaselo claramente y ofrece de inmediato una solución (Fraccionamiento sin intereses o Ahorro con Movistar Total).
"""


# =========================================================
# 2. DEFINICIÓN DE HERRAMIENTAS PARA FUNCTION CALLING
# =========================================================

def tool_consultar_recibo(cliente_id: str, periodo: str = "2026-07") -> str:
    """Consulta y audita el recibo del cliente para obtener la variación exacta y sus causas."""
    res = consultar_recibo(cliente_id, periodo)
    return json.dumps(res, ensure_ascii=False)


def tool_evaluar_upgrade_movistar_total(cliente_id: str) -> str:
    """Evalúa la elegibilidad y calcula el plan óptimo de Movistar Total con ahorro financiero real."""
    res = evaluar_upgrade_movistar_total(cliente_id)
    return json.dumps(res, ensure_ascii=False)


def tool_solicitar_escalacion_humana(cliente_id: str, motivo: str) -> str:
    """Transfiere el caso a un asesor humano generando un ticket en la cola de atención CRM."""
    t_id = solicitar_derivacion_humana(cliente_id, motivo)
    return json.dumps({"ticket_id": t_id, "status": "PENDIENTE", "motivo": motivo}, ensure_ascii=False)


def tool_consultar_descuentos_prorrateos(cliente_id: str) -> str:
    """Consulta la ficha completa de descuentos vigentes y prorrateos registrados en base de datos."""
    res = get_ficha_cliente_completa(cliente_id)
    return json.dumps(res, ensure_ascii=False)


TOOLS_MAPPING = {
    "consultar_recibo": tool_consultar_recibo,
    "evaluar_upgrade_movistar_total": tool_evaluar_upgrade_movistar_total,
    "solicitar_escalacion_humana": tool_solicitar_escalacion_humana,
    "consultar_descuentos_prorrateos": tool_consultar_descuentos_prorrateos
}


# =========================================================
# 3. NORMALIZADOR LINGÜÍSTICO PERUANO (PRE-PROCESAMIENTO)
# =========================================================

DICCIONARIO_JERGA_PERUANA = {
    r"\blucas\b": "soles",
    r"\bmangos\b": "soles",
    r"\blukitas\b": "soles",
    r"\bmano\b": "amigo",
    r"\bcausa\b": "amigo",
    r"\bchoche\b": "amigo",
    r"\bpata\b": "amigo",
    r"\bhabla pe\b": "hola",
    r"\bhabla\b": "hola",
    r"\boe\b": "oye",
    r"\bxq\b": "por qué",
    r"\bpq\b": "por qué",
    r"\bm\b": "me",
    r"\bd\b": "de",
    r"\bq\b": "que",
    r"\btmb\b": "también",
    r"\bxfa\b": "por favor",
    r"\bplz\b": "por favor",
    r"\bal toque\b": "de inmediato",
    r"\basao\b": "molesto",
    r"\basado\b": "molesto"
}


def normalizar_texto_coloquial(texto: str) -> str:
    """
    Normaliza jergas peruanas y abreviaturas frecuentes para facilitar
    la clasificación semántica sin alterar el sentido de la consulta.
    """
    texto_norm = texto.lower()
    for patron, reemplazo in DICCIONARIO_JERGA_PERUANA.items():
        texto_norm = re.sub(patron, reemplazo, texto_norm, flags=re.IGNORECASE)
    return texto_norm


# =========================================================
# 4. MOTOR PRINCIPAL: GET_GEMINI_RESPONSE
# =========================================================

def get_gemini_response(
    chat_history: List[Dict[str, Any]],
    user_message: str,
    client_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Procesa el mensaje del usuario utilizando Google Gemini (si está configurada la API Key)
    o mediante el motor determinista de Yara AI con comprensión de jergas y 0% alucinaciones.

    Retorna un diccionario estructurado con:
      - 'response_text': str
      - 'action_payload': Optional[dict] (disparador de tarjetas/botones en UI)
      - 'tool_calls_executed': list
      - 'model_used': str
    """
    client_ctx = client_context or {}
    cid = str(client_ctx.get("id") or client_ctx.get("cliente_id") or "CLI001").strip().upper()
    
    tools_executed = []
    action_payload = None

    # Normalizar consulta para interpretar jergas peruanas
    user_query_norm = normalizar_texto_coloquial(user_message)

    # 1. Verificar si requiere escalamiento inmediato a humano
    debe_escalar, tipo_disp, motivo = detectar_necesidad_escalamiento(user_query_norm, chat_history, cid)
    if debe_escalar:
        ticket = escalar_a_humano(cid, chat_history, motivo, prioridad="ALTA" if "GRAVE" in tipo_disp else "MEDIA")
        t_id = ticket["ticket_id"]
        tools_executed.append({"tool": "solicitar_escalacion_humana", "result": ticket})
        
        return {
            "response_text": (
                f"🔔 **He transferido tu caso a uno de nuestros asesores especializados.** En breve te atenderán con todo el detalle de tu consulta.\n\n"
                f"• **Ticket de Atención Asignado:** **`{t_id}`**\n"
                f"• **Motivo Registrado:** *{motivo}*\n"
                f"• **Estado:** `PENDIENTE EN COLA PRIORITARIA`\n\n"
                f"El asesor asignado revisará la conversación previa para brindarte una solución inmediata."
            ),
            "action_payload": {"action": "TRIGGER_ESCALATION", "ticket_id": t_id},
            "tool_calls_executed": tools_executed,
            "model_used": "Yara-AI-EscalationEngine"
        }

    # 2. Si contamos con SDK de Google Gemini y API Key válida, ejecutar con GenerativeModel
    if HAS_GENAI_LIB and config.HAS_GEMINI_KEY:
        try:
            genai.configure(api_key=config.GEMINI_API_KEY)
            
            # Instanciar modelo con System Instruction y baja temperatura
            model = genai.GenerativeModel(
                model_name=config.GEMINI_MODEL,
                generation_config={
                    "temperature": config.GEMINI_TEMPERATURE,
                    "top_p": 0.95,
                    "max_output_tokens": 1024
                },
                system_instruction=YARA_SYSTEM_PROMPT
            )

            # Ejecutar herramientas deterministas para inyectar datos reales
            recibo_data = consultar_recibo(cid)
            nbo_data = evaluar_upgrade_movistar_total(cid)
            ficha_data = get_ficha_cliente_completa(cid)

            contexto_prompt = f"""
            DATOS REALES DEL CLIENTE (FUENTE VERIFICADA):
            - ID Cliente: {cid}
            - Nombre: {client_ctx.get('nombre', 'Cliente')}
            - Servicio Actual: {client_ctx.get('servicio', 'Fijo/Móvil')}
            - Auditoría Recibo Actual (Julio 2026): {json.dumps(recibo_data, ensure_ascii=False)}
            - Recomendación Movistar Total: {json.dumps(nbo_data, ensure_ascii=False)}
            - Ficha Técnica y Descuentos: {json.dumps(ficha_data, ensure_ascii=False)}

            CONSULTA DEL CLIENTE:
            "{user_message}"
            (Versión interpretada: "{user_query_norm}")

            Instrucciones para Yara AI:
            Responde empáticamente interpretando las dudas del cliente y usando ESTRICTAMENTE los datos numéricos arriba expuestos. 0% alucinaciones.
            """

            response = model.generate_content(contexto_prompt)
            respuesta_texto = response.text.strip() if response.text else "No encuentro ese registro en tu cuenta actual."

            # Detección de acciones UI
            if "movistar total" in user_query_norm or "upgrade" in user_query_norm:
                action_payload = {"action": "SHOW_UPGRADE_CARD", "nbo": nbo_data}
            elif "fraccionar" in user_query_norm or "cuotas" in user_query_norm:
                action_payload = {"action": "SHOW_INSTALLMENT_MODAL", "monto": client_ctx.get("recibo_actual", 119.90)}

            return {
                "response_text": respuesta_texto,
                "action_payload": action_payload,
                "tool_calls_executed": [{"tool": "consultar_recibo"}, {"tool": "evaluar_upgrade_movistar_total"}],
                "model_used": f"Google-Gemini ({config.GEMINI_MODEL})"
            }

        except Exception as e:
            # Fallback transparente al motor determinista de Yara AI
            pass

    # 3. Motor Determinista de Yara AI (Comprensión Coloquial & 0% Alucinaciones)
    return _ejecutar_yara_determinista(cid, user_query_norm, user_message, client_ctx)


def _ejecutar_yara_determinista(
    client_id: str,
    query_norm: str,
    original_query: str,
    client_ctx: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Motor determinista de alta fidelidad que implementa las reglas de Yara AI
    con comprensión del registro peruano ("lucas", "mano", "xq", "promo") y Tool Calling.
    """
    tools_executed = []
    action_payload = None

    # Consulta de Variación de Recibo / Por qué subió / Cobros de más ("lucas más", "xq m vino")
    if any(k in query_norm for k in ["por qué", "porque", "por que", "subio", "subió", "aumento", "aumentó", "soles mas", "soles más", "cobro", "recibo", "factura", "caro", "diferencia", "promo", "descuento"]):
        recibo_info = consultar_recibo(client_id)
        tools_executed.append({"tool": "consultar_recibo", "result": recibo_info})

        if not recibo_info.get("encontrado"):
            return {
                "response_text": "No encuentro ese registro en tu cuenta actual. Si crees que se trata de un error, puedo comunicarte con un asesor humano.",
                "action_payload": None,
                "tool_calls_executed": tools_executed,
                "model_used": "Yara-AI-Deterministic"
            }

        var = recibo_info.get("variacion", {})
        monto_var = var.get("monto", 0.0) if var else 0.0
        pct_var = var.get("porcentaje", 0.0) if var else 0.0
        conceptos = recibo_info.get("conceptos_adicionales", [])

        if monto_var == 0.0 or not conceptos:
            return {
                "response_text": (
                    f"¡Hola! He auditado tu recibo de Julio 2026 y **no presenta ningún incremento** respecto al mes anterior.\n\n"
                    f"Tu tarifa base se mantiene idéntica y no tienes cargos adicionales activos."
                ),
                "action_payload": None,
                "tool_calls_executed": tools_executed,
                "model_used": "Yara-AI-Deterministic"
            }

        desglose = []
        for c in conceptos:
            c_nom = c.get("concepto", "")
            c_monto = c.get("monto", 0.0)
            c_tipo = c.get("tipo", "")

            if "repetidor" in c_nom.lower() or c_tipo == "cargo_unico":
                desglose.append(f"• **{c_nom} (+S/ {c_monto:.2f})**: Es un cobro por única vez por la instalación del equipo que solicitaste el mes pasado.")
            elif "descuento" in c_nom.lower() or c_tipo == "fin_descuento":
                desglose.append(f"• **{c_nom} (+S/ {c_monto:.2f})**: Finalizó tu periodo promocional con descuento temporal, regresando a la tarifa regular del plan.")
            elif c_tipo == "prorrateo":
                desglose.append(f"• **{c_nom} (+S/ {c_monto:.2f})**: Es un cobro proporcional por los días de servicio usados entre tu cambio de plan y la fecha de corte.")
            elif c_tipo == "cuota_equipo":
                desglose.append(f"• **{c_nom} (+S/ {c_monto:.2f})**: Corresponde a la cuota mensual del equipo móvil financiado en tu contrato.")
            elif c_tipo == "cargo_reconexion":
                desglose.append(f"• **{c_nom} (+S/ {c_monto:.2f})**: Es el cargo administrativo por la reconexión de tu servicio tras un pago fuera de fecha.")
            else:
                desglose.append(f"• **{c_nom} (+S/ {c_monto:.2f})**: Concepto registrado en tu ciclo de facturación.")

        txt_desglose = "\n".join(desglose)
        return {
            "response_text": (
                f"¡Hola! Te explico con total claridad lo que ocurrió con tu recibo de Julio 2026:\n\n"
                f"Tu recibo tuvo una variación de **+S/ {monto_var:.2f} (+{pct_var:.2f}%)** por los siguientes motivos exactos:\n\n"
                f"{txt_desglose}\n\n"
                f"💡 *Si deseas facilidades de pago, puedes fraccionar tu recibo sin intereses o evaluar un plan convergente Movistar Total para ahorrar.*"
            ),
            "action_payload": {"action": "SHOW_INSTALLMENT_OPTION", "variacion": var},
            "tool_calls_executed": tools_executed,
            "model_used": "Yara-AI-Deterministic"
        }

    # Solicitud de Movistar Total / Upgrade / Ahorro
    if any(k in query_norm for k in ["total", "upgrade", "migrar", "ahorrar", "ahorro", "convergente", "unificar", "oferta", "promocion", "promoción", "mejorar"]):
        nbo_data = evaluar_upgrade_movistar_total(client_id)
        tools_executed.append({"tool": "evaluar_upgrade_movistar_total", "result": nbo_data})

        if not nbo_data.get("encontrado"):
            return {
                "response_text": "No encuentro ese registro en tu cuenta actual.",
                "action_payload": None,
                "tool_calls_executed": tools_executed,
                "model_used": "Yara-AI-Deterministic"
            }

        of = nbo_data.get("oferta_recomendada", {})
        ben = nbo_data.get("beneficio_economico", {})

        if nbo_data.get("es_elegible_mt"):
            action_payload = {"action": "SHOW_UPGRADE_CARD", "nbo": nbo_data}
            return {
                "response_text": (
                    f"🚀 **¡Buenas noticias! Eres elegible para Movistar Total.**\n\n"
                    f"En lugar de pagar tus servicios por separado (gasto aprox. **S/ {ben.get('gasto_actual_fragmentado_estimado', 0):.2f}/mes**), te sugerimos unificar todo:\n\n"
                    f"• **Plan Recomendado:** {of.get('nombre_oferta')}\n"
                    f"• **Fibra Simétrica:** {of.get('velocidad_mbps')} Mbps\n"
                    f"• **Líneas Móviles:** {of.get('gigas_datos')} GB en alta velocidad\n"
                    f"• **Precio Promocional:** **S/ {of.get('precio_promocional'):.2f} / mes**\n"
                    f"• **Ahorro Real Mensual:** 💰 **S/ {ben.get('ahorro_mensual_soles', 0):.2f} ({ben.get('ahorro_porcentaje', 0):.1f}%)**\n"
                    f"• **Ahorro Anual Proyectado:** **S/ {ben.get('ahorro_anual_estimado_soles', 0):.2f} al año**\n\n"
                    f"¿Deseas que activemos tu solicitud de migración?"
                ),
                "action_payload": action_payload,
                "tool_calls_executed": tools_executed,
                "model_used": "Yara-AI-Deterministic"
            }
        else:
            return {
                "response_text": (
                    f"Actualmente cuentas con tu plan optimizado o ya dispones del beneficio Movistar Total. "
                    f"Te sugerimos una mejora de velocidad a **{of.get('nombre_oferta')}** por **S/ {of.get('precio_promocional'):.2f}/mes**."
                ),
                "action_payload": None,
                "tool_calls_executed": tools_executed,
                "model_used": "Yara-AI-Deterministic"
            }

    # Fraccionamiento de Deuda
    if any(k in query_norm for k in ["fraccionar", "fraccionamiento", "cuotas", "pagar en partes", "diferir", "deuda"]):
        monto_actual = client_ctx.get("recibo_actual", 119.90)
        return {
            "response_text": (
                f"💳 **Planes de Fraccionamiento sin Intereses (TCEA 0.0%):**\n\n"
                f"Para tu recibo actual de **S/ {monto_actual:.2f}**, puedes elegir:\n"
                f"• **3 cuotas fijas** de **S/ {(monto_actual/3):.2f} / mes**\n"
                f"• **6 cuotas fijas** de **S/ {(monto_actual/6):.2f} / mes**\n"
                f"• **12 cuotas fijas** de **S/ {(monto_actual/12):.2f} / mes**\n\n"
                f"Puedes seleccionarlo directamente en la pestaña de Soluciones Comerciales en tu pantalla."
            ),
            "action_payload": {"action": "SHOW_INSTALLMENT_MODAL", "monto": monto_actual},
            "tool_calls_executed": tools_executed,
            "model_used": "Yara-AI-Deterministic"
        }

    # Saludos
    if any(k in query_norm for k in ["hola", "buenos dias", "buenas tardes", "buenas noches", "hey", "ayuda"]):
        nombre = client_ctx.get("nombre", "Cliente")
        return {
            "response_text": (
                f"¡Hola {nombre}! Soy **Yara AI**, tu asistente inteligente de Movistar Perú. 📱\n\n"
                f"Puedo ayudarte a:\n"
                f"1. **Explicarte con exactitud por qué varió tu recibo de julio**.\n"
                f"2. **Calcular tu ahorro con Movistar Total (hasta 50%)**.\n"
                f"3. **Fraccionar tu deuda en cuotas sin intereses**.\n"
                f"4. **Transferirte con un asesor humano** si requieres atención especial.\n\n"
                f"¿En qué te puedo ayudar hoy?"
            ),
            "action_payload": None,
            "tool_calls_executed": tools_executed,
            "model_used": "Yara-AI-Deterministic"
        }

    # Fallback estricto Anti-Alucinaciones
    return {
        "response_text": (
            f"Comprendo tu consulta: '{original_query}'. "
            f"Para esa información puntual: *No encuentro ese registro en tu cuenta actual* (No dispongo de ese dato en su facturación actual). "
            f"¿Deseas que te comunique con un asesor humano para revisarlo a detalle?"
        ),
        "action_payload": None,
        "tool_calls_executed": tools_executed,
        "model_used": "Yara-AI-Deterministic"
    }
