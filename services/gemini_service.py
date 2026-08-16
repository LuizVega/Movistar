"""
services/gemini_service.py - Motor de Inteligencia Generativa y Razonamiento Yara AI (Google Gemini)
Respuestas ultra cortas (1-2 oraciones), empáticas, directas, sin spam de Movistar Total.
"""

import os
import json
import urllib.request
import urllib.error
import re
from typing import Dict, Any, List, Optional

import config
from services.agent_service import (
    consultar_recibo,
    evaluar_upgrade_movistar_total
)
from database import get_ficha_cliente_completa
from services.escalation_service import detectar_necesidad_escalamiento, escalar_a_humano


# =========================================================
# 1. SYSTEM PROMPT ULTRA CONCISO Y ASERTIVO
# =========================================================

YARA_SYSTEM_PROMPT = """
Eres YARA AI, la copiloto experta y resolutiva de facturación de Movistar Perú.

### REGLAS FUNDAMENTALES:
1. **EXTREMA CONCISIÓN**: Responde en **1 o 2 oraciones breves (máximo 20 a 35 palabras)**. Sé directa, clara y humana. NUNCA escribas párrafos largos.
2. **CERO SPAM DE MOVISTAR TOTAL**: 
   - NUNCA ofrezcas Movistar Total al inicio ni cuando el cliente solo pregunta sobre su recibo, un cargo puntual o por qué subió su cuenta.
   - Resuelve primero la duda del cliente con amabilidad y datos exactos de su cuenta.
   - **SOLO** menciona Movistar Total como una sugerencia opcional al despedirte cuando el cliente ya entendió y agradece (*"gracias"*, *"ok entendido"*, *"listo"*), o si el cliente pide expresamente cotizar o cambiar de plan.
3. **0% ALUCINACIONES**: Toda cifra en Soles (S/) y motivo de cobro provienen de los datos reales del cliente.
4. **COMPRENSIÓN TOTAL**: Entiendes jergas peruanas (oe, lucas, mangos, pe, causa, poq, xq, fonoi) y preguntas de seguimiento ("q es eso?", "¿cuánto pago por cada cosa?").
5. **CONSULTAS FUERA DE ALCANCE**: Si preguntan temas no relacionados (política, luna, recetas), responde en una sola frase breve que solo atiendes servicios de Movistar.
"""

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
    r"\bey\b": "hola",
    r"\bm\b": "me",
    r"\bta\b": "está",
    r"\btoy\b": "estoy",
    r"\bx\b": "por",
    r"\bd\b": "de",
    r"\bk\b": "que",
    r"\bq\b": "que",
    r"\bfonoi\b": "teléfono",
    r"\bfono\b": "teléfono",
    r"\blenteja\b": "lento",
    r"\basao\b": "molesto"
}


def normalizar_texto_coloquial(texto: str) -> str:
    """Limpia y normaliza el texto para comprensión de jergas y abreviaturas."""
    t = texto.lower().strip()
    for patron, reemplazo in DICCIONARIO_NORMALIZACION.items():
        t = re.sub(patron, reemplazo, t, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", t).strip()


def clasificar_intencion_y_keys(query_original: str) -> Dict[str, Any]:
    """Clasifica intenciones clave para trazabilidad."""
    q = normalizar_texto_coloquial(query_original)
    scores = {"GREETING": 0.0, "BILLING_INCREASE": 0.0, "PRICE_COMPLAINT_OR_SAVINGS": 0.0, "OUT_OF_SCOPE": 0.0, "GENERAL_INFO": 0.0}
    
    if any(k in q for k in ["por qué", "subio", "subió", "aumento", "recibo", "mas", "más", "cobran de mas", "cobran", "cobro"]):
        scores["BILLING_INCREASE"] = 0.9
    elif any(k in q for k in ["caro", "mucho", "pagar menos", "ahorro", "bajar plan"]):
        scores["PRICE_COMPLAINT_OR_SAVINGS"] = 0.85
    elif any(k in q for k in ["presidente", "luna", "receta", "futbol"]):
        scores["OUT_OF_SCOPE"] = 0.95
    elif any(q == s or q.startswith(s + " ") for s in ["hola", "hi", "hello", "oye", "habla"]):
        scores["GREETING"] = 0.8
    else:
        scores["GENERAL_INFO"] = 0.7

    top = max(scores.items(), key=lambda x: x[1])[0]
    return {
        "top_intent": top,
        "score": scores[top],
        "intention_scores": scores,
        "keys_detected": []
    }


# =========================================================
# 2. LLAMADA REST A GOOGLE GEMINI (ALTA VELOCIDAD)
# =========================================================

def _call_gemini_rest(prompt: str, api_key: str, model_name: str = "gemini-flash-lite-latest") -> Optional[str]:
    """Realiza una petición HTTP POST directa a la API de Gemini."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 150
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=6) as response:
            data = json.loads(response.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
    except Exception:
        pass
    return None


# =========================================================
# 3. MOTOR PRINCIPAL: GET_GEMINI_RESPONSE
# =========================================================

def get_gemini_response(
    chat_history: List[Dict[str, Any]],
    user_message: str,
    client_context: Optional[Dict[str, Any]] = None,
    api_key_override: Optional[str] = None
) -> Dict[str, Any]:
    """Procesa la consulta con respuestas ultra cortas, precisas y sin spam comercial."""
    client_ctx = client_context or {}
    cid = str(client_ctx.get("id") or client_ctx.get("cliente_id") or "CLI001").strip().upper()
    nombre_cliente = client_ctx.get("nombre", "Cliente").split()[0]
    
    recibo_data = consultar_recibo(cid)
    nbo_data = evaluar_upgrade_movistar_total(cid)

    # Verificar escalamiento explícito a humano
    msg_clean = user_message.lower().strip()
    pide_asesor = any(k in msg_clean for k in ["hablar con un asesor", "comunicarme con un asesor", "pasame con un asesor", "pásame con un asesor", "transferir con un asesor", "quiero un humano", "libro de reclamaciones"])
    if pide_asesor:
        ticket = escalar_a_humano(cid, chat_history, "Solicitud directa de asesor", prioridad="ALTA")
        t_id = ticket["ticket_id"]
        return {
            "response_text": f"Hola {nombre_cliente}, he derivado tu caso a un asesor con tu Ticket de Atención **`{t_id}`**.",
            "action_payload": {"action": "TRIGGER_ESCALATION", "ticket_id": t_id},
            "tool_calls_executed": [{"tool": "solicitar_escalacion_humana", "result": ticket}],
            "model_used": "Yara-AI-EscalationEngine"
        }

    var_info = recibo_data.get("variacion") or {}
    conceptos = recibo_data.get("conceptos_adicionales") or []
    motivo_var = conceptos[0]["concepto"] if conceptos else client_ctx.get("motivo_principal", "Ajuste de facturación")
    monto_var = var_info.get("monto", client_ctx.get("diferencia", 0.0))
    recibo_ant = float(client_ctx.get("recibo_anterior", 89.90))
    recibo_act = float(client_ctx.get("recibo_actual", 119.90))
    beneficios_cliente = client_ctx.get("beneficios_actuales", "tu velocidad de fibra simétrica y minutos ilimitados")

    of = nbo_data.get("oferta_recomendada", {})
    ben = nbo_data.get("beneficio_economico", {})
    nombre_mt = of.get("nombre_oferta", "Movistar Total Dúo 200 Mbps + 1 Línea")
    precio_mt = float(of.get("precio_promocional", 110.40))
    ahorro_soles = float(ben.get("ahorro_mensual_soles", 29.40))
    puede_cross_selling = bool(ahorro_soles > 0 and client_ctx.get("tipo_servicio") in ["HOGAR_Y_MOVIL", "HOGAR", "SOLO_HOGAR"])

    # Formatear historial
    historial_formateado = []

    for h in chat_history[-6:]:
        role_label = "Cliente" if h.get("role") == "user" else "Yara AI"
        historial_formateado.append(f"{role_label}: {h.get('content')}")
    historial_str = "\n".join(historial_formateado) if historial_formateado else "Inicio de conversación."

    tiene_intencion_especifica = any(k in msg_clean for k in ["total", "upgrade", "cambiar", "ahorr", "fraccion", "recibo", "subio", "subió", "por qué", "porque", "cobro", "lucas", "menos", "cuanto", "cuánto", "pago", "mas", "más", "vino", "promo", "diferencia", "desglose", "detalle"])
    es_saludo_inicial = len(chat_history) == 0 and not tiene_intencion_especifica and any(msg_clean == s or msg_clean.startswith(s + " ") for s in ["hola", "hi", "hello", "buenas", "oye", "habla", "ey", "buenos dias", "buenas tardes", "buenas noches"])


    prompt_gemini = f"""
{YARA_SYSTEM_PROMPT}

DATOS REALES DEL CLIENTE (AUDITADOS):
- Nombre: {nombre_cliente} ({cid})
- Plan actual: {client_ctx.get('plan_actual', 'Plan Fibra')}
- Tarifa regular base: S/ {recibo_ant:.2f}/mes (facturada en junio).
- Recibo de Julio: S/ {recibo_act:.2f} (incluye variación de +S/ {monto_var:.2f} por '{motivo_var}').
- Línea móvil: {client_ctx.get('telefono_movil', '987654321')} ({client_ctx.get('estado_linea_movil', 'ACTIVA')}).
- Beneficios actuales ya activos: {beneficios_cliente}

HISTORIAL DE CHARLA:
{historial_str}

NUEVO MENSAJE DEL CLIENTE:
"{user_message}"

INSTRUCCIONES CLAVE:
1. Responde en **MÁXIMO 1 O 2 ORACIONES (20 a 30 palabras)** con un tono humano, horizontal y transparente.
2. Si el cliente pregunta cuánto paga o por qué subió, explícale con total claridad que su tarifa base es S/ {recibo_ant:.2f} y que los +S/ {monto_var:.2f} corresponden a '{motivo_var}'.
3. Si el cliente pregunta cuánto paga por internet y cuánto por móvil, aclara que su plan base es S/ {recibo_ant:.2f} y el repetidor/adicional es S/ {monto_var:.2f}.
4. Si el cliente pide explícitamente información de Movistar Total o cambio de plan, dale el precio de S/ {precio_mt:.2f} y el ahorro mensual de S/ {ahorro_soles:.2f}.
5. EFECTO EFERVESCENTE: Si el cliente agradece o finaliza ('gracias', 'listo', 'entendido'), despídete recordando con calidez los beneficios que ya tiene en su plan actual ('{beneficios_cliente}'), sin ofrecer adiciones nuevas.
6. De lo contrario, NO ofrezcas Movistar Total y limítate a resolver exactamente lo que preguntó.
"""

    gemini_key = api_key_override or os.environ.get("GEMINI_API_KEY") or config.GEMINI_API_KEY
    if gemini_key and len(gemini_key) > 10:
        raw_reply = _call_gemini_rest(prompt_gemini, gemini_key, "gemini-flash-lite-latest")

        if raw_reply:
            resp_lower = raw_reply.lower()
            msg_lower = user_message.lower()
            action_payload = None

            # Determinar componente visual adjunto y acciones recomendadas
            if es_saludo_inicial:
                action_payload = {"action": "SHOW_DASHBOARD"}
            elif any(p in msg_lower for p in ["cambiar de plan", "cambiar plan", "quiero ver planes", "promocion total", "movistar total", "alternativas comerciales"]):
                action_payload = {"action": "SHOW_UPGRADE_CARD", "nbo": nbo_data}
            elif any(p in msg_lower for p in ["fraccionar", "cuotas", "diferir"]):
                action_payload = {"action": "SHOW_INSTALLMENT_MODAL", "monto": recibo_act}
            elif any(p in msg_lower for p in ["por qué", "porque", "subio", "subió", "cobran de mas", "recibo", "desglose", "detalle", "cuanto pago", "cuánto pago", "vino mas", "vino más"]):
                action_payload = {
                    "action": "SHOW_ACTIONS_HUB",
                    "variacion": var_info,
                    "nbo": nbo_data if puede_cross_selling else None,
                    "puede_cross_selling": puede_cross_selling,
                    "motivo_var": motivo_var
                }

            return {
                "response_text": raw_reply,
                "action_payload": action_payload,
                "tool_calls_executed": [{"tool": "consultar_recibo"}],
                "model_used": "Google Gemini (gemini-flash-lite-latest)"
            }

    # =========================================================
    # 4. MOTOR SEMÁNTICO LOCAL DE RESPALDO (EN CASO DE CORTE DE API)
    # =========================================================
    action_payload = None
    msg_low = user_message.lower().strip()

    if es_saludo_inicial or any(msg_low == s or msg_low.startswith(s + " ") for s in ["hola", "hi", "hello", "buenas", "oye", "habla"]):
        resp_text = f"¡Hola {nombre_cliente}! Dime en qué te puedo apoyar hoy con tu servicio de Movistar."
        action_payload = {"action": "SHOW_DASHBOARD"}

    elif any(p in msg_low for p in ["cuanto pago", "cuánto pago", "desglose", "detalle"]):
        resp_text = (
            f"Tu plan base es de **S/ {recibo_ant:.2f}/mes**. En julio pagas **S/ {recibo_act:.2f}** "
            f"porque se sumaron **S/ {monto_var:.2f}** por {motivo_var.lower()}."
        )
        action_payload = {
            "action": "SHOW_ACTIONS_HUB",
            "variacion": var_info,
            "nbo": nbo_data if puede_cross_selling else None,
            "puede_cross_selling": puede_cross_selling,
            "motivo_var": motivo_var
        }

    elif any(p in msg_low for p in ["q es eso", "que es eso", "q significa", "que significa"]):
        if "repetidor" in motivo_var.lower():
            resp_text = f"Es el cobro único de **S/ {monto_var:.2f}** por la instalación de tu repetidor WiFi. El próximo mes tu recibo vuelve a **S/ {recibo_ant:.2f}**."
        elif "reconexión" in motivo_var.lower() or "moros" in motivo_var.lower():
            resp_text = f"Es el cargo único de **S/ {monto_var:.2f}** por reactivar tu línea tras suspensión. No se repetirá si pagas a tiempo."
        else:
            resp_text = f"Corresponde a un cargo de **S/ {monto_var:.2f}** por {motivo_var.lower()}."

    elif any(p in msg_low for p in ["subio", "subió", "por qué", "porque", "cobran de mas", "caro", "mucho", "vino mas", "vino más"]):
        resp_text = (
            f"Tranquilo {nombre_cliente}, tu plan normal es de **S/ {recibo_ant:.2f}**. "
            f"Este mes subió a **S/ {recibo_act:.2f}** por el cobro de **S/ {monto_var:.2f}** por {motivo_var.lower()}."
        )
        action_payload = {
            "action": "SHOW_ACTIONS_HUB",
            "variacion": var_info,
            "nbo": nbo_data if puede_cross_selling else None,
            "puede_cross_selling": puede_cross_selling,
            "motivo_var": motivo_var
        }

    elif any(p in msg_low for p in ["gracias", "listo", "entendido", "ok", "vale", "ya entendi"]):
        resp_text = f"¡Un placer, {nombre_cliente}! Recuerda que tu plan ya incluye {beneficios_cliente} para disfrutar en casa. ¡Que tengas un excelente día!"

    elif any(p in msg_low for p in ["cambiar plan", "cambiar de plan", "movistar total", "unificar", "upgrade", "ahorro", "alternativas"]):
        resp_text = f"Puedes migrar a **{nombre_mt}** por solo **S/ {precio_mt:.2f}/mes**, con un ahorro mensual de **S/ {ahorro_soles:.2f}** en tu cuenta."
        action_payload = {"action": "SHOW_UPGRADE_CARD", "nbo": nbo_data}

    else:
        resp_text = f"Hola {nombre_cliente}, tu plan actual es de **S/ {recibo_ant:.2f}/mes**. ¿Qué detalle deseas revisar?"

    return {
        "response_text": resp_text,
        "action_payload": action_payload,
        "tool_calls_executed": [{"tool": "consultar_recibo"}],
        "model_used": "Yara-AI-SemanticEngine"
    }

