"""
services/gemini_service.py - Motor de Inteligencia Generativa y Razonamiento Yara AI (Google Gemini)
Equipado con criterio de asesor comercial inteligente, mensajes concisos sin muros de texto,
dashboard visual al inicio y recomendación oportuna de Movistar Total solo cuando realmente aporta valor.
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
# 1. SYSTEM PROMPT MAESTRO DE ASESOR COMERCIAL INTELIGENTE
# =========================================================

YARA_SYSTEM_PROMPT = """
Eres YARA AI, la asesora comercial y copiloto experta de facturación de Movistar Perú.

### POLÍTICA DE 0% ALUCINACIONES:
- Toda cifra en Soles (S/), nombres de planes, fechas y motivos de cobro provienen EXCLUSIVAMENTE de los datos reales del cliente en el contexto.

### ESTILO DE COMUNICACIÓN (CONCISO Y DIRECTO):
- Escribe respuestas CORTAS, AMABLES Y AL GRANO (máximo 1 a 2 párrafos breves, 40 a 70 palabras).
- NUNCA generes muros de texto largos que aburran al cliente. Sé cercana, empática y pedagógica.

### CRITERIO COMERCIAL Y VENTA ASERTIVA DE MOVISTAR TOTAL:
- Actúa como una vendedora inteligente y perspicaz: **NO ofrezcas Movistar Total en todas las respuestas ni de forma invasiva**.
- Si el cliente solo tiene una duda puntual (ej. "¿qué es reconexión?", "¿por qué me cobran el repetidor?", "¿cuándo vence mi recibo?"), **limítate a responder su duda con claridad y amabilidad**.
- **¿CUÁNDO SÍ RECOMENDAR MOVISTAR TOTAL?**:
  * Cuando el cliente pregunte expresamente por ahorro, rebajas, cambio de plan o unificar servicios (*"quiero pagar menos"*, *"¿cómo ahorro?"*, *"¿qué planes hay?"*).
  * Y cuando el cálculo tenga sentido lógico real (comparando su gasto conjunto de Hogar + Línea Móvil vs el precio de Movistar Total).
  * Ejemplo de explicación matemática con sentido: *"Actualmente gastas aprox. S/ 140 pagando tu internet y celular por separado. Al unificarlos en Movistar Total pagarías S/ 110.40/mes, ahorrando S/ 29.40 al mes"*.
- Si el cliente tiene un plan básico de S/ 79.90 y solo reclama un cobro puntual de S/ 10, **NO le ofrezcas un plan de S/ 110.40**. Explícale el cargo puntual y ofrécele facilidades de pago o fraccionamiento.

### COMPRENSIÓN LINGÜÍSTICA Y MODISMOS:
- Entiendes a la perfección modismos peruanos (lucas, mangos, pe, causa, habla, poq, xq) e inglés básico (hi, hello).

### PRIMER SALUDO / INICIO:
- Saluda afectuosamente por su nombre, dile que en pantalla tiene el resumen clave de su cuenta y pregúntale en qué puedes apoyarlo hoy.


### CONSULTAS FUERA DE ALCANCE:
- Si preguntan temas no relacionados a Movistar (política, luna, recetas), responde brevemente y con simpatía que estás para ayudarlo con sus servicios de Movistar.
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

def _call_gemini_rest(prompt: str, api_key: str, model_name: str = "gemini-3.5-flash-lite") -> Optional[str]:
    """Realiza una petición HTTP POST directa a la API de Gemini sin intermediarios."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 350
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
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
    """
    Procesa la consulta del usuario invocando Google Gemini en vivo con memoria multi-turno completa,
    contexto financiero auditado y criterio de venta inteligente y concisa.
    """
    client_ctx = client_context or {}
    cid = str(client_ctx.get("id") or client_ctx.get("cliente_id") or "CLI001").strip().upper()
    nombre_cliente = client_ctx.get("nombre", "Cliente").split()[0]
    
    # 1. Cargar datos auditados del cliente
    recibo_data = consultar_recibo(cid)
    nbo_data = evaluar_upgrade_movistar_total(cid)

    # 2. Verificar escalamiento directo explícito a humano
    msg_clean = user_message.lower().strip()
    pide_asesor_directo = any(k in msg_clean for k in ["hablar con un asesor", "comunicarme con un asesor", "pasame con un asesor", "pásame con un asesor", "transferir con un asesor", "quiero un humano", "libro de reclamaciones"])
    if pide_asesor_directo:
        ticket = escalar_a_humano(cid, chat_history, "Solicitud de atención por asesor humano", prioridad="ALTA")
        t_id = ticket["ticket_id"]
        return {
            "response_text": (
                f"Hola {nombre_cliente}, he registrado tu caso con prioridad y lo transferí a un asesor especializado.\n\n"
                f"• **Ticket de Atención:** **`{t_id}`**\n"
                f"• **Estado:** `PENDIENTE EN BANDEJA CRM`"
            ),
            "action_payload": {"action": "TRIGGER_ESCALATION", "ticket_id": t_id},
            "tool_calls_executed": [{"tool": "solicitar_escalacion_humana", "result": ticket}],
            "model_used": "Yara-AI-EscalationEngine"
        }

    # 3. Contexto estructurado para Gemini
    var_info = recibo_data.get("variacion") or {}
    conceptos = recibo_data.get("conceptos_adicionales") or []
    motivo_var = conceptos[0]["concepto"] if conceptos else client_ctx.get("motivo_principal", "Ajuste de facturación")
    monto_var = var_info.get("monto", client_ctx.get("diferencia", 0.0))
    recibo_ant = float(client_ctx.get("recibo_anterior", 89.90))
    recibo_act = float(client_ctx.get("recibo_actual", 119.90))

    of = nbo_data.get("oferta_recomendada", {})
    ben = nbo_data.get("beneficio_economico", {})
    nombre_mt = of.get("nombre_oferta", "Movistar Total Dúo 200 Mbps + 1 Línea")
    precio_mt = float(of.get("precio_promocional", 110.40))
    gasto_total_actual = float(ben.get("gasto_actual_fragmentado_estimado", recibo_ant + 49.90))
    ahorro_soles = float(ben.get("ahorro_mensual_soles", max(gasto_total_actual - precio_mt, 0.0)))
    es_elegible_mt = nbo_data.get("es_elegible_mt", False)

    # Formatear historial de conversación
    historial_formateado = []
    for h in chat_history[-6:]:
        role_label = "Cliente" if h.get("role") == "user" else "Yara AI"
        historial_formateado.append(f"{role_label}: {h.get('content')}")
    historial_str = "\n".join(historial_formateado) if historial_formateado else "Inicio de conversación."

    tiene_intencion_especifica = any(k in msg_clean for k in ["total", "upgrade", "cambiar", "ahorr", "fraccion", "recibo", "subio", "subió", "por qué", "porque", "cobro", "lucas", "menos"])
    es_saludo_inicial = len(chat_history) == 0 and not tiene_intencion_especifica and any(msg_clean == s or msg_clean.startswith(s + " ") for s in ["hola", "hi", "hello", "buenas", "oye", "habla", "ey", "buenos dias", "buenas tardes", "buenas noches"])


    prompt_gemini = f"""
{YARA_SYSTEM_PROMPT}

DATOS REALES DEL CLIENTE (AUDITADOS):
- Nombre: {nombre_cliente} ({cid})
- Plan: {client_ctx.get('plan_actual', 'Plan Fibra')}
- Recibo Anterior: S/ {recibo_ant:.2f} | Recibo Actual: S/ {recibo_act:.2f} (Variación de +S/ {monto_var:.2f} por '{motivo_var}')
- Línea Móvil: {client_ctx.get('telefono_movil', '987654321')} ({client_ctx.get('estado_linea_movil', 'ACTIVA')})
- Gasto Combinado Hogar + Celular estimado: S/ {gasto_total_actual:.2f}/mes
- Movistar Total: {nombre_mt} a S/ {precio_mt:.2f}/mes (Ahorro real de S/ {ahorro_soles:.2f}/mes). Elegible: {es_elegible_mt}.

HISTORIAL DE CHARLA:
{historial_str}

NUEVO MENSAJE DEL CLIENTE:
"{user_message}"

INSTRUCCIONES CLAVE PARA ESTE MENSAJE:
1. Responde de forma CONCISA (máximo 1 a 2 párrafos cortos, máximo 50-70 palabras).
2. Si es saludo de inicio, saluda a {nombre_cliente}, indícale que adjuntas el resumen de su plan en pantalla y pregúntale cómo puedes apoyarlo.
3. Si pregunta sobre qué es '{motivo_var}', explícaselo en 2 oraciones sencillas y aclárale si es un cobro por única vez.
4. NO ofrezcas Movistar Total si solo está preguntando por qué subió su recibo o qué es un cargo puntual. Solo ofrécelo si pide opciones de ahorro, rebajas, cambio de plan o si el cliente lo solicita.
"""

    gemini_key = api_key_override or os.environ.get("GEMINI_API_KEY") or config.GEMINI_API_KEY
    if gemini_key and len(gemini_key) > 10:
        raw_reply = _call_gemini_rest(prompt_gemini, gemini_key, "gemini-3.5-flash-lite")
        if not raw_reply:
            raw_reply = _call_gemini_rest(prompt_gemini, gemini_key, "gemini-3.5-flash")

        if raw_reply:
            resp_lower = raw_reply.lower()
            msg_lower = user_message.lower()
            action_payload = None

            # Determinar componente visual adjunto
            if es_saludo_inicial:
                action_payload = {"action": "SHOW_DASHBOARD"}
            elif any(p in msg_lower for p in ["cambiar de plan", "cambiar plan", "quiero ahorrar", "promocion total", "movistar total", "unificar"]):
                action_payload = {"action": "SHOW_UPGRADE_CARD", "nbo": nbo_data}
            elif any(p in msg_lower for p in ["fraccionar", "cuotas", "diferir"]):
                action_payload = {"action": "SHOW_INSTALLMENT_MODAL", "monto": recibo_act}
            elif any(p in msg_lower for p in ["por qué", "porque", "subio", "subió", "cobran de mas", "recibo", "desglose", "detalle"]):
                action_payload = {"action": "SHOW_BILLING_BREAKDOWN", "variacion": var_info}
            elif "asesor" in resp_lower and ("transferir" in resp_lower or "ticket" in resp_lower):
                action_payload = {"show_action_buttons": ["ASESOR"]}

            return {
                "response_text": raw_reply,
                "action_payload": action_payload,
                "tool_calls_executed": [{"tool": "consultar_recibo"}],
                "model_used": "Google Gemini (gemini-3.5-flash)"
            }

    # =========================================================
    # 4. MOTOR SEMÁNTICO LOCAL DE RESPALDO (EN CASO DE CORTE DE API)
    # =========================================================
    action_payload = None
    msg_low = user_message.lower().strip()

    if es_saludo_inicial or any(msg_low == s or msg_low.startswith(s + " ") for s in ["hola", "hi", "hello", "buenas", "oye", "habla"]):
        resp_text = f"¡Hola {nombre_cliente}! Dime en qué te puedo ayudar hoy. Aquí tienes el resumen clave de tu plan y facturación actual:"
        action_payload = {"action": "SHOW_DASHBOARD"}

    elif any(p in msg_low for p in ["q es eso", "que es eso", "q significa", "que significa", "a que se debe"]):
        if "reconexión" in motivo_var.lower() or "moros" in motivo_var.lower():
            resp_text = (
                f"El **Cargo por Reconexión** (S/ {monto_var:.2f}) es el cobro administrativo por reactivar tu servicio tras una suspensión por pago fuera de fecha. "
                f"Es un cobro por única vez y no se repetirá si mantienes tus pagos al día."
            )
        elif "repetidor" in motivo_var.lower():
            resp_text = (
                f"Corresponde a la **Instalación del Repetidor WiFi** (S/ {monto_var:.2f}) solicitado para ampliar la cobertura en tu hogar. "
                f"Es un pago único y no vendrá en tus siguientes recibos."
            )
        elif "descuento" in motivo_var.lower():
            resp_text = f"Significa que venció el descuento promocional de tu plan, regresando a su tarifa regular de S/ {recibo_act:.2f}."
        else:
            resp_text = f"El concepto **{motivo_var}** corresponde a un cargo auditado de S/ {monto_var:.2f} en tu recibo de julio."

    elif any(p in msg_low for p in ["cambiar plan", "cambiar de plan", "ahorrar", "unificar", "movistar total"]):
        resp_text = (
            f"Al unificar tu internet y tu línea móvil en **{nombre_mt}** pagarías solo **S/ {precio_mt:.2f}/mes**, "
            f"ahorrando **S/ {ahorro_soles:.2f} al mes** respecto a tu gasto actual."
        )
        action_payload = {"action": "SHOW_UPGRADE_CARD", "nbo": nbo_data}

    elif any(p in msg_low for p in ["subio", "subió", "por qué", "porque", "cobran de mas", "recibo"]):
        resp_text = f"Hola {nombre_cliente}, tu recibo subió **S/ {monto_var:.0f}** debido a {motivo_var.lower()}."
        action_payload = {"action": "SHOW_BILLING_BREAKDOWN", "variacion": var_info}

    elif any(p in msg_low for p in ["caro", "mucho", "no me alcanza"]):
        resp_text = (
            f"Te entiendo, {nombre_cliente}. Podemos ayudarte fraccionando tu recibo actual en cuotas sin intereses "
            f"o evaluando si te conviene unificar servicios para pagar menos en total. ¿Qué prefieres revisar?"
        )

    else:
        resp_text = f"Hola {nombre_cliente}, ¿en qué consulta sobre tu recibo o servicio de Movistar te puedo apoyar?"

    return {
        "response_text": resp_text,
        "action_payload": action_payload,
        "tool_calls_executed": [{"tool": "consultar_recibo"}],
        "model_used": "Yara-AI-SemanticEngine"
    }
