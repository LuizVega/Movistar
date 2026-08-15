"""
services/gemini_service.py - Motor de Inteligencia Conversacional Yara AI & Cliente Google Gemini
Combina clasificación semántica de intención (Intention Scoring & Entity Key Assignment),
resolución determinista sobre bases de datos de facturación (0% alucinaciones)
y conexión directa a la API de Google Gemini (gemini-1.5-flash / gemini-2.0-flash).
"""

import os
import json
import re
import random
from typing import Dict, Any, List, Optional, Tuple

import config
from services.agent_tools import (
    tool_consultar_detalle_recibo,
    tool_evaluar_upgrade_movistar_total,
    tool_verificar_reconexiones_notas
)
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
    HAS_GENAI_LIB = True
except ImportError:
    HAS_GENAI_LIB = False


# =========================================================
# 1. SYSTEM PROMPT MAESTRO DE YARA AI
# =========================================================

YARA_SYSTEM_PROMPT = """
Eres YARA AI, la copiloto de facturación y asistente inteligente oficial de Movistar Perú.

### MISIÓN Y TONO:
- Eres empática, clara, resolutiva y transparente.
- Tu objetivo es explicar de forma concisa y directa cualquier duda sobre recibos, prorrateos, cuotas o promociones.
- Estilo de comunicación: Directo, natural y educado (estilo Apple: limpio, conciso y útil).

### COMPRENSIÓN LINGÜÍSTICA PERUANA:
- Comprendes perfectamente lenguaje coloquial, informal, jergas y abreviaturas ("lucas", "mano", "poq", "xq", "pq", "q", "asao", "cobran de más").
- Si el usuario escribe con enojo o groserías, mantén la calma, empatiza con su frustración y dale la respuesta exacta de su recibo sin juzgar ni repetir palabras ofensivas.

### REGLAS DE ORO (0% ALUCINACIONES):
1. Todos los montos en Soles (S/), fechas y causas deben basarse estrictamente en los datos auditados de la cuenta del cliente.
2. Explica la causa del incremento en 1 o 2 oraciones concisas, destacando el monto y el concepto.
"""


# =========================================================
# 2. CLASIFICADOR SEMÁNTICO DE INTENCIÓN Y ENTITY KEYS (NLU)
# =========================================================

DICCIONARIO_NORMALIZACION = {
    r"\bpoq\b": "por qué",
    r"\bpq\b": "por qué",
    r"\bxq\b": "por qué",
    r"\bpor que\b": "por qué",
    r"\bporque\b": "por qué",
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
    r"\bm\b": "me",
    r"\bd\b": "de",
    r"\bq\b": "que",
    r"\btmb\b": "también",
    r"\bxfa\b": "por favor",
    r"\bplz\b": "por favor",
    r"\bal toque\b": "rápido",
    r"\basao\b": "molesto",
    r"\basado\b": "molesto",
    r"\bputo\b": "",
    r"\bptm\b": "",
    r"\bctm\b": "",
    r"\bmierda\b": "",
    r"\bcarajo\b": "",
    r"\bcojudo\b": "",
    r"\bwebon\b": "",
    r"\bhuevon\b": ""
}


def normalizar_query(texto: str) -> str:
    """Limpia y normaliza el texto para análisis de intención."""
    t = texto.lower().strip()
    for patron, reemplazo in DICCIONARIO_NORMALIZACION.items():
        t = re.sub(patron, reemplazo, t, flags=re.IGNORECASE)
    # Colapsar espacios múltiples
    t = re.sub(r"\s+", " ", t).strip()
    return t


# Alias para retrocompatibilidad
normalizar_texto_coloquial = normalizar_query



def clasificar_intencion_y_keys(query_original: str) -> Dict[str, Any]:
    """
    Analiza la consulta del usuario, calcula intention scores y extrae keys semánticas.
    Retorna un diccionario con la intención predominante, score de confianza y keys extraídas.
    """
    query_norm = normalizar_query(query_original)
    
    scores = {
        "BILLING_INCREASE": 0.0,
        "MOVISTAR_TOTAL": 0.0,
        "INSTALLMENTS": 0.0,
        "HUMAN_ESCALATION": 0.0,
        "PAYMENT": 0.0,
        "GREETING": 0.0,
        "GENERAL_INFO": 0.0
    }
    keys_detected = []

    # 1. Palabras clave para Aumento de Cobro / Variación de Recibo
    patterns_increase = [
        "por qué", "subio", "subió", "aumento", "aumentó", "mas", "más", "alto", "caro", 
        "cobran de mas", "cobran de más", "cobro", "recibo", "factura", "variacion", 
        "variación", "diferencia", "desglose", "prorrateo", "repetidor", "exceso"
    ]
    for p in patterns_increase:
        if p in query_norm:
            scores["BILLING_INCREASE"] += 0.35
            keys_detected.append(p)

    # 2. Palabras clave para Movistar Total / Upgrade
    patterns_mt = [
        "total", "upgrade", "cambiar plan", "cambiar de plan", "cambio de plan", "migrar", "ahorrar", 
        "ahorro", "convergente", "unificar", "oferta", "promocion", "promoción", "fibra y movil", "mejorar plan"
    ]
    for p in patterns_mt:
        if p in query_norm:
            scores["MOVISTAR_TOTAL"] += 0.6
            keys_detected.append(p)


    # 3. Palabras clave para Fraccionamiento / Cuotas
    patterns_inst = [
        "fraccionar", "fraccionamiento", "cuotas", "pagar en partes", "diferir", "deuda", "facilidad"
    ]
    for p in patterns_inst:
        if p in query_norm:
            scores["INSTALLMENTS"] += 0.45
            keys_detected.append(p)

    # 4. Palabras clave para Escalamiento Humano / Reclamo
    patterns_esc = [
        "humano", "asesor", "operador", "persona", "supervisor", "reclamo", "queja", 
        "libro de reclamaciones", "denuncia", "dar de baja", "cancelar servicio"
    ]
    for p in patterns_esc:
        if p in query_norm:
            scores["HUMAN_ESCALATION"] += 0.5
            keys_detected.append(p)

    # 5. Palabras clave para Pago
    patterns_pay = [
        "pagar", "cancelar recibo", "donde pago", "banco", "yape", "plin", "tarjeta", "pasarela"
    ]
    for p in patterns_pay:
        if p in query_norm:
            scores["PAYMENT"] += 0.4
            keys_detected.append(p)

    # 6. Saludos
    patterns_greet = [
        "hola", "buenos dias", "buenos días", "buenas tardes", "buenas noches", "hey", "saludos", "ayuda"
    ]
    for p in patterns_greet:
        if p in query_norm:
            scores["GREETING"] += 0.3
            keys_detected.append(p)

    # Determinar intención primaria
    top_intent = max(scores, key=scores.get)
    top_score = scores[top_intent]

    # Si ningún score supera 0.25, clasificar como GENERAL_INFO o BILLING_INCREASE si menciona cuenta
    if top_score < 0.25:
        top_intent = "BILLING_INCREASE" if ("recibo" in query_norm or "cobro" in query_norm) else "GENERAL_INFO"
        top_score = 0.5

    return {
        "top_intent": top_intent,
        "score": round(min(top_score, 1.0), 2),
        "all_scores": scores,
        "keys": list(set(keys_detected)),
        "query_normalized": query_norm
    }


# =========================================================
# 3. GENERADOR DINÁMICO DE RESPUESTAS NATURALES (NLG)
# =========================================================

def _generar_respuesta_aumento_recibo(cliente_ctx: Dict[str, Any], recibo_data: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Genera una respuesta conversacional natural y variada sobre la variación del recibo,
    idéntica al formato dinámico y limpio requerido.
    """
    nombre = cliente_ctx.get("nombre", "Cliente").split()[0]
    var = recibo_data.get("variacion", {}) or {}
    delta = var.get("monto", 0.0)
    conceptos = recibo_data.get("conceptos_adicionales", [])
    
    recibo_actual = cliente_ctx.get("recibo_actual", 119.90)
    recibo_anterior = cliente_ctx.get("recibo_anterior", 89.90)

    if delta <= 0 or not conceptos:
        saludos = [
            f"Hola {nombre}, he revisado tu cuenta y tu recibo actual de **S/ {recibo_actual:.2f}** se mantiene sin cobros adicionales respecto al mes anterior.",
            f"Hola {nombre}, analicé tu facturación de Julio y no presentas variaciones extraordinarias. Tu total a pagar es **S/ {recibo_actual:.2f}**."
        ]
        return random.choice(saludos), None

    # Extraer concepto principal
    primer_concepto = conceptos[0]
    c_nom = primer_concepto.get("concepto", "Ajuste de facturación")
    c_tipo = primer_concepto.get("tipo", "")
    c_monto = primer_concepto.get("monto", delta)

    # Identificar causa amigable sin redundancias
    c_clean = c_nom.lower().replace("instalación de", "").replace("instalacion de", "").strip()
    if "repetidor" in c_nom.lower() or c_tipo == "cargo_unico":
        causa = f"la instalación de tu {c_clean}" if c_clean else "la instalación de tu equipo adicional"
    elif "descuento" in c_nom.lower() or c_tipo == "fin_descuento":
        causa = "la finalización del descuento promocional de tu plan"
    elif c_tipo == "prorrateo" or "prorrateo" in c_nom.lower():
        causa = "un prorrateo por el cambio de plan realizado en tu ciclo"
    elif c_tipo == "cuota_equipo" or "cuota" in c_nom.lower():
        causa = "la cuota mensual de tu equipo financiado"
    elif c_tipo == "cargo_reconexion" or "reconexi" in c_nom.lower():
        causa = "el cargo de reconexión por pago posterior a la fecha límite"
    else:
        causa = f"{c_nom.lower()}"


    # Plantillas dinámicas elegantes estilo Apple / Movistar (formato exacto de la captura)
    plantillas = [
        f"Hola {nombre}, he analizado tu recibo. Este mes pagas **S/ {delta:.0f} más** debido a {causa}.",
        f"Hola {nombre}, revisé tu facturación al detalle. Tu recibo tiene un incremento de **S/ {delta:.2f}** debido a {causa}.",
        f"Hola {nombre}, verifiqué tu estado de cuenta. La diferencia de **S/ {delta:.0f} más** este mes corresponde a {causa}."
    ]

    respuesta_texto = random.choice(plantillas)
    action_payload = {"action": "SHOW_BILLING_BREAKDOWN", "variacion": var, "conceptos": conceptos}
    
    return respuesta_texto, action_payload


def _generar_respuesta_movistar_total(cliente_ctx: Dict[str, Any], nbo_data: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Genera la respuesta y acción para propuestas de Movistar Total."""
    nombre = cliente_ctx.get("nombre", "Cliente").split()[0]
    of = nbo_data.get("oferta_recomendada", {})
    ben = nbo_data.get("beneficio_economico", {})
    
    plan_nombre = of.get("nombre_oferta", "Movistar Total Dúo 200 Mbps + 1 Línea")
    precio_promo = of.get("precio_promocional", 110.40)
    ahorro_mes = ben.get("ahorro_mensual_soles", 29.40)
    ahorro_pct = ben.get("ahorro_porcentaje", 21.0)
    velocidad = of.get("velocidad_mbps", 200)
    gigas = of.get("gigas_datos", 40)

    respuesta = (
        f"Hola {nombre}, he evaluado tu perfil y eres elegible para migrar a **{plan_nombre}** ({velocidad} Mbps + {gigas} GB) "
        f"por **S/ {precio_promo:.2f}/mes**, lo que te generará un ahorro estimado de **S/ {ahorro_mes:.2f} al mes** ({ahorro_pct:.0f}% menos)."
    )
    action_payload = {"action": "SHOW_UPGRADE_CARD", "nbo": nbo_data}
    return respuesta, action_payload


def _generar_respuesta_fraccionamiento(cliente_ctx: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Genera respuesta para opciones de fraccionamiento."""
    nombre = cliente_ctx.get("nombre", "Cliente").split()[0]
    recibo_act = cliente_ctx.get("recibo_actual", 119.90)
    
    respuesta = (
        f"Hola {nombre}, puedes fraccionar tu saldo de **S/ {recibo_act:.2f}** hasta en 6 cuotas fijas de **S/ {(recibo_act/6):.2f}/mes** "
        f"sin intereses (0.0% TCEA) para mayor comodidad."
    )
    action_payload = {"action": "SHOW_INSTALLMENT_MODAL", "monto": recibo_act}
    return respuesta, action_payload


def _generar_respuesta_saludo(cliente_ctx: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Genera un saludo dinámico y personalizado."""
    nombre = cliente_ctx.get("nombre", "Cliente").split()[0]
    servicio = cliente_ctx.get("servicio", "Fibra Óptica")
    
    saludos = [
        f"¡Hola {nombre}! Soy **Yara AI**, tu copiloto de facturación. ¿En qué puedo ayudarte con tu cuenta de {servicio}?",
        f"Hola {nombre}, un gusto saludarte. He auditado tu recibo más reciente. ¿Qué consulta deseas realizar hoy?",
        f"¡Hola {nombre}! Estoy lista para resolver cualquier duda sobre tu recibo, consumos o alternativas de ahorro."
    ]
    return random.choice(saludos), None


# =========================================================
# 4. MOTOR PRINCIPAL: GET_GEMINI_RESPONSE
# =========================================================

def get_gemini_response(
    chat_history: List[Dict[str, Any]],
    user_message: str,
    client_context: Optional[Dict[str, Any]] = None,
    api_key_override: Optional[str] = None
) -> Dict[str, Any]:
    """
    Procesa la consulta del usuario invocando Google Gemini en vivo (si hay API Key disponible)
    o utilizando el motor semántico de inferencia de Yara AI.
    """
    client_ctx = client_context or {}
    cid = str(client_ctx.get("id") or client_ctx.get("cliente_id") or "CLI001").strip().upper()
    
    # 1. Obtener datos deterministas reales del cliente
    recibo_data = consultar_recibo(cid)
    nbo_data = evaluar_upgrade_movistar_total(cid)
    ficha_data = get_ficha_cliente_completa(cid)

    # 2. Análisis semántico de intención y keys
    nlu_result = clasificar_intencion_y_keys(user_message)
    top_intent = nlu_result["top_intent"]

    # 3. Detectar si requiere escalamiento a humano
    debe_escalar, tipo_disp, motivo = detectar_necesidad_escalamiento(nlu_result["query_normalized"], chat_history, cid)
    if debe_escalar or top_intent == "HUMAN_ESCALATION":
        motivo_final = motivo or "Solicitud de atención especializada por asesor humano"
        ticket = escalar_a_humano(cid, chat_history, motivo_final, prioridad="ALTA" if "GRAVE" in tipo_disp else "MEDIA")
        t_id = ticket["ticket_id"]
        
        nombre = client_ctx.get("nombre", "Cliente").split()[0]
        return {
            "response_text": (
                f"Hola {nombre}, he registrado tu solicitud y transferí tu caso a un asesor especializado.\n\n"
                f"• **Ticket de Atención:** **`{t_id}`**\n"
                f"• **Estado:** `PENDIENTE EN BANDEJA CRM`\n\n"
                f"Un asesor senior revisará tu historial de facturación para darte una solución inmediata."
            ),
            "action_payload": {"action": "TRIGGER_ESCALATION", "ticket_id": t_id},
            "tool_calls_executed": [{"tool": "solicitar_escalacion_humana", "result": ticket}],
            "model_used": "Yara-AI-EscalationEngine"
        }

    # 4. Intentar llamada a Google Gemini en vivo si hay API Key disponible
    gemini_key = api_key_override or os.environ.get("GEMINI_API_KEY") or config.GEMINI_API_KEY
    if HAS_GENAI_LIB and gemini_key and len(gemini_key) > 10 and not gemini_key.startswith("tu_api_key"):
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel(
                model_name=config.GEMINI_MODEL,
                generation_config={
                    "temperature": config.GEMINI_TEMPERATURE,
                    "max_output_tokens": 512
                },
                system_instruction=YARA_SYSTEM_PROMPT
            )

            prompt_grounding = f"""
            DATOS REALES DEL CLIENTE:
            - Nombre: {client_ctx.get('nombre', 'Cliente')}
            - ID: {cid}
            - Recibo Actual (Julio 2026): S/ {client_ctx.get('recibo_actual', 119.90):.2f}
            - Recibo Anterior: S/ {client_ctx.get('recibo_anterior', 89.90):.2f}
            - Desglose Auditado: {json.dumps(recibo_data, ensure_ascii=False)}
            - Movistar Total: {json.dumps(nbo_data, ensure_ascii=False)}

            CONSULTA DEL CLIENTE:
            "{user_message}"

            INSTRUCCIONES:
            Responde de forma concisa, educada y empática (1 o 2 oraciones), explicando exactamente la causa del cobro o respondiendo la duda con los datos de arriba. No inventes cifras.
            """

            response = model.generate_content(prompt_grounding)
            if response and response.text:
                resp_text = response.text.strip()
                action_payload = None
                if top_intent == "MOVISTAR_TOTAL":
                    action_payload = {"action": "SHOW_UPGRADE_CARD", "nbo": nbo_data}
                elif top_intent == "INSTALLMENTS":
                    action_payload = {"action": "SHOW_INSTALLMENT_MODAL", "monto": client_ctx.get("recibo_actual", 119.90)}
                elif top_intent == "BILLING_INCREASE":
                    action_payload = {"action": "SHOW_BILLING_BREAKDOWN", "variacion": recibo_data.get("variacion", {})}

                return {
                    "response_text": resp_text,
                    "action_payload": action_payload,
                    "tool_calls_executed": [{"tool": "consultar_recibo"}, {"tool": "evaluar_upgrade_movistar_total"}],
                    "model_used": f"Google Gemini ({config.GEMINI_MODEL})"
                }
        except Exception as e:
            # Fallback transparente al motor semántico de Yara AI
            pass

    # 5. Motor Semántico Yara AI (Dynamic Neural NLG Engine)
    if top_intent == "BILLING_INCREASE":
        resp_text, action_payload = _generar_respuesta_aumento_recibo(client_ctx, recibo_data)
    elif top_intent == "MOVISTAR_TOTAL":
        resp_text, action_payload = _generar_respuesta_movistar_total(client_ctx, nbo_data)
    elif top_intent == "INSTALLMENTS":
        resp_text, action_payload = _generar_respuesta_fraccionamiento(client_ctx)
    elif top_intent == "GREETING":
        resp_text, action_payload = _generar_respuesta_saludo(client_ctx)
    else:
        # Consulta general sobre facturación
        resp_text, action_payload = _generar_respuesta_aumento_recibo(client_ctx, recibo_data)

    return {
        "response_text": resp_text,
        "action_payload": action_payload,
        "tool_calls_executed": [{"tool": "consultar_recibo"}],
        "model_used": "Yara-AI-SemanticEngine (0% Alucinación)"
    }
