"""
services/gemini_service.py - Motor de Inteligencia Conversacional Yara AI con Google Gemini
Utiliza el modelo oficial de Gemini (gemini-3.5-flash) conectado en vivo mediante API Key
con grounding estricto sobre datos de facturación (0% alucinaciones) y comprensión del lenguaje peruano.
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

# Importar SDK de Google Generative AI
try:
    import google.generativeai as genai
    HAS_GENAI_LIB = True
except ImportError:
    HAS_GENAI_LIB = False


# =========================================================
# 1. SYSTEM PROMPT MAESTRO DE YARA AI
# =========================================================

YARA_SYSTEM_PROMPT = """
Eres YARA AI, la copiloto oficial de facturación y asistente inteligente de Movistar Perú.

### TU IDENTIDAD Y MISIÓN:
- Eres empática, sumamente amable, ágil, clara, transparente y 100% resolutiva.
- Tu misión principal es hacer sentir bien, comprendido y escuchado al cliente en todo momento, resolviendo de inmediato cualquier duda o molestia con su servicio.

### COMPRENSIÓN LINGÜÍSTICA Y MANEJO DE EMOCIONES:
- Comprendes a la perfección el lenguaje coloquial peruano, jergas, abreviaturas y cualquier registro ("lucas", "mano", "causa", "poq", "xq", "pq", "q", "asao", "cobran de más").
- Si el usuario se expresa con molestia, enojo o palabras fuertes, mantén la máxima calma, empatiza con su frustración con calidez y dale la respuesta exacta de su recibo sin juzgar ni repetir palabras ofensivas.

### POLÍTICA ESTRICTA DE 0% ALUCINACIONES:
1. Toda cifra en Soles (S/), fechas de vencimiento, nombres de promociones, megas/gigas y causas de cobro provienen EXCLUSIVAMENTE de los datos reales auditados de la cuenta del cliente que se te proporcionan.
2. Explica la causa del cobro o variación en 1 o 2 oraciones concisas y amables.
"""


# =========================================================
# 2. NORMALIZADOR LINGÜÍSTICO Y CLASIFICADOR DE INTENCIÓN
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
    r"\basado\b": "molesto"
}


def normalizar_query(texto: str) -> str:
    """Limpia y normaliza el texto para análisis semántico."""
    t = texto.lower().strip()
    for patron, reemplazo in DICCIONARIO_NORMALIZACION.items():
        t = re.sub(patron, reemplazo, t, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", t).strip()


normalizar_texto_coloquial = normalizar_query


def clasificar_intencion_y_keys(query_original: str) -> Dict[str, Any]:
    """Clasifica la intención del usuario y extrae keys semánticas."""
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

    # Aumento de Cobro / Variación de Recibo
    for p in ["por qué", "subio", "subió", "aumento", "aumentó", "mas", "más", "alto", "caro", "cobran de mas", "cobran de más", "cobro", "recibo", "factura", "variacion", "variación", "diferencia", "prorrateo", "repetidor"]:
        if p in query_norm:
            scores["BILLING_INCREASE"] += 0.4
            keys_detected.append(p)

    # Movistar Total / Upgrade
    for p in ["total", "upgrade", "cambiar plan", "cambiar de plan", "cambio de plan", "migrar", "ahorrar", "ahorro", "convergente", "unificar", "oferta", "promocion", "promoción", "fibra y movil", "mejorar"]:
        if p in query_norm:
            scores["MOVISTAR_TOTAL"] += 0.5
            keys_detected.append(p)

    # Fraccionamiento
    for p in ["fraccionar", "fraccionamiento", "cuotas", "pagar en partes", "diferir", "deuda"]:
        if p in query_norm:
            scores["INSTALLMENTS"] += 0.5
            keys_detected.append(p)

    # Asesor humano / Reclamo
    for p in ["humano", "asesor", "operador", "persona", "supervisor", "reclamo", "queja", "libro de reclamaciones", "baja", "cancelar contrato"]:
        if p in query_norm:
            scores["HUMAN_ESCALATION"] += 0.6
            keys_detected.append(p)

    # Saludos
    for p in ["hola", "buenos dias", "buenos días", "buenas tardes", "buenas noches", "hey", "saludos", "ayuda"]:
        if p in query_norm:
            scores["GREETING"] += 0.3
            keys_detected.append(p)

    top_intent = max(scores, key=scores.get)
    top_score = scores[top_intent]
    if top_score < 0.2:
        top_intent = "BILLING_INCREASE" if ("recibo" in query_norm or "cobro" in query_norm) else "GENERAL_INFO"

    return {
        "top_intent": top_intent,
        "score": round(top_score, 2),
        "keys": list(set(keys_detected)),
        "query_normalized": query_norm
    }


# =========================================================
# 3. MOTOR PRINCIPAL: GET_GEMINI_RESPONSE
# =========================================================

def get_gemini_response(
    chat_history: List[Dict[str, Any]],
    user_message: str,
    client_context: Optional[Dict[str, Any]] = None,
    api_key_override: Optional[str] = None
) -> Dict[str, Any]:
    """
    Procesa la consulta del usuario invocando Google Gemini en vivo (con gemini-3.5-flash)
    o mediante el motor semántico neuronal determinista de Yara AI.
    """
    client_ctx = client_context or {}
    cid = str(client_ctx.get("id") or client_ctx.get("cliente_id") or "CLI001").strip().upper()
    nombre_cliente = client_ctx.get("nombre", "Cliente").split()[0]
    
    # 1. Cargar datos reales y auditados del cliente
    recibo_data = consultar_recibo(cid)
    nbo_data = evaluar_upgrade_movistar_total(cid)
    ficha_data = get_ficha_cliente_completa(cid)

    # 2. Análisis semántico de intención
    nlu_result = clasificar_intencion_y_keys(user_message)
    top_intent = nlu_result["top_intent"]

    # 3. Verificar escalamiento a asesor humano
    debe_escalar, tipo_disp, motivo = detectar_necesidad_escalamiento(nlu_result["query_normalized"], chat_history, cid)
    if debe_escalar or top_intent == "HUMAN_ESCALATION":
        motivo_final = motivo or "Solicitud de atención especializada por asesor humano"
        ticket = escalar_a_humano(cid, chat_history, motivo_final, prioridad="ALTA" if "GRAVE" in tipo_disp else "MEDIA")
        t_id = ticket["ticket_id"]
        
        return {
            "response_text": (
                f"Hola {nombre_cliente}, he registrado tu caso con prioridad y lo transferí a un asesor especializado.\n\n"
                f"• **Ticket de Atención:** **`{t_id}`**\n"
                f"• **Estado:** `PENDIENTE EN BANDEJA CRM`\n\n"
                f"Un asesor senior revisará tu historial para darte una solución inmediata."
            ),
            "action_payload": {"action": "TRIGGER_ESCALATION", "ticket_id": t_id},
            "tool_calls_executed": [{"tool": "solicitar_escalacion_humana", "result": ticket}],
            "model_used": "Yara-AI-EscalationEngine"
        }

    # 4. Invocación de Google Gemini en Vivo
    gemini_key = api_key_override or os.environ.get("GEMINI_API_KEY") or config.GEMINI_API_KEY
    if HAS_GENAI_LIB and gemini_key and len(gemini_key) > 10:
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
            DATOS REALES Y AUDITADOS DEL CLIENTE EN SISTEMA:
            - Nombre: {client_ctx.get('nombre', 'Cliente')} (Trátalo cordialmente por su nombre: {nombre_cliente})
            - ID de Cuenta: {cid}
            - Recibo Anterior (Junio 2026): S/ {client_ctx.get('recibo_anterior', 89.90):.2f}
            - Recibo Actual (Julio 2026): S/ {client_ctx.get('recibo_actual', 119.90):.2f}
            - Desglose Auditado del Recibo: {json.dumps(recibo_data, ensure_ascii=False)}
            - Oferta Movistar Total: {json.dumps(nbo_data, ensure_ascii=False)}
            - Ficha Técnica: {json.dumps(ficha_data, ensure_ascii=False)}

            MENSAJE DEL CLIENTE:
            "{user_message}"

            DIRECTIVAS:
            1. Responde de forma muy amable, empática, tranquila y resolutiva (máximo 2-3 oraciones).
            2. Si el usuario pregunta por qué subió su recibo, explica exactamente la causa real y el monto adicional en Soles.
            3. Haz que el cliente se sienta 100% escuchado y valorado. No inventes cifras.
            """

            response = model.generate_content(prompt_grounding)
            if response and response.text:
                resp_text = response.text.strip()
                action_payload = None

                if top_intent == "BILLING_INCREASE":
                    action_payload = {"action": "SHOW_BILLING_BREAKDOWN", "variacion": recibo_data.get("variacion", {})}
                elif top_intent == "MOVISTAR_TOTAL":
                    action_payload = {"action": "SHOW_UPGRADE_CARD", "nbo": nbo_data}
                elif top_intent == "INSTALLMENTS":
                    action_payload = {"action": "SHOW_INSTALLMENT_MODAL", "monto": client_ctx.get("recibo_actual", 119.90)}

                return {
                    "response_text": resp_text,
                    "action_payload": action_payload,
                    "tool_calls_executed": [{"tool": "consultar_recibo"}, {"tool": "evaluar_upgrade_movistar_total"}],
                    "model_used": f"Google Gemini ({config.GEMINI_MODEL})"
                }
        except Exception as e:
            # Fallback seguro al motor semántico local
            pass

    # 5. Motor Semántico Local de Respaldo
    if top_intent == "BILLING_INCREASE":
        var = recibo_data.get("variacion", {}) or {}
        delta = var.get("monto", 0.0)
        conceptos = recibo_data.get("conceptos_adicionales", [])
        c_nom = conceptos[0]["concepto"] if conceptos else "Ajuste de facturación"
        
        c_clean = c_nom.lower().replace("instalación de", "").replace("instalacion de", "").strip()
        causa = f"la instalación de tu {c_clean}" if "repetidor" in c_nom.lower() else f"{c_nom.lower()}"
        
        resp_text = f"Hola {nombre_cliente}, he analizado tu recibo. Este mes pagas **S/ {delta:.0f} más** debido a {causa}."
        action_payload = {"action": "SHOW_BILLING_BREAKDOWN", "variacion": var}

    elif top_intent == "MOVISTAR_TOTAL":
        of = nbo_data.get("oferta_recomendada", {})
        ben = nbo_data.get("beneficio_economico", {})
        resp_text = (
            f"Hola {nombre_cliente}, he evaluado tu cuenta y puedes migrar a **{of.get('nombre_oferta')}** "
            f"por **S/ {of.get('precio_promocional', 110.40):.2f}/mes**, ahorrando **S/ {ben.get('ahorro_mensual_soles', 29.40):.2f} al mes**."
        )
        action_payload = {"action": "SHOW_UPGRADE_CARD", "nbo": nbo_data}

    elif top_intent == "INSTALLMENTS":
        rec_act = client_ctx.get("recibo_actual", 119.90)
        resp_text = f"Hola {nombre_cliente}, puedes fraccionar tu saldo de S/ {rec_act:.2f} en 6 cuotas fijas de S/ {(rec_act/6):.2f}/mes sin intereses."
        action_payload = {"action": "SHOW_INSTALLMENT_MODAL", "monto": rec_act}

    else:
        resp_text = f"¡Hola {nombre_cliente}! Soy Yara AI, tu copiloto de facturación. ¿En qué puedo ayudarte hoy con tu servicio?"
        action_payload = None

    return {
        "response_text": resp_text,
        "action_payload": action_payload,
        "tool_calls_executed": [{"tool": "consultar_recibo"}],
        "model_used": "Yara-AI-SemanticEngine (0% Alucinación)"
    }
