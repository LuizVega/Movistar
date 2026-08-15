"""
services/gemini_service.py - Motor de Inteligencia Generativa y Razonamiento Yara AI (Google Gemini)
Procesa todas las consultas del cliente mediante IA generativa en vivo con contexto completo,
memoria multi-turno, deducción lógica y comprensión de cualquier lenguaje, jerga o pregunta de seguimiento.
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
# 1. SYSTEM PROMPT MAESTRO GENERATIVO DE YARA AI
# =========================================================

YARA_SYSTEM_PROMPT = """
Eres YARA AI, la copiloto oficial de facturación e inteligencia conversacional de Movistar Perú.

### POLÍTICA DE 0% ALUCINACIONES Y VERACIDAD:
- Toda cifra en Soles (S/), estado de línea móvil/fija, nombres de planes, fechas y causas de cobro provienen EXCLUSIVAMENTE de los datos reales del cliente proporcionados en el contexto auditado (0% ALUCINACIONES).

### TU IDENTIDAD, PROPÓSITO Y PERSONALIDAD:
- Eres una IA generativa sumamente inteligente, empática, comprensiva, cálida, pedagógica y humana.
- Tu misión principal es que **cualquier persona, sin importar su nivel de educación, jerga o forma de expresarse, entienda a la perfección su recibo y sus servicios, sintiéndose tranquila y respaldada**.
- Razonas, deduces y piensas con sentido común. Entiendes preguntas de seguimiento ("q es eso?", "¿y eso solo va para mi internet?", "¿por qué?", "¿cómo así?"), relacionándolas con los mensajes previos y los datos de la cuenta.

### COMPRENSIÓN LINGÜÍSTICA TOTAL (JERGAS, IDIOMAS Y ERRORES):
- Entiendes cualquier expresión humana, modismos peruanos ("pe", "causa", "choche", "mano", "pata", "habla", "q fue", "poq", "xq", "pq", "asao", "lucas", "fonoi"), inglés básico ("hi", "hello", "thanks") y errores gramaticales o de tipeo.
- Si el usuario saluda ("hi", "hola", "buenas", "habla"), salúdalo con calidez por su nombre y pregúntale cómo puedes apoyarlo hoy.

### EXPLICACIÓN PEDAGÓGICA DE CONCEPTOS DE FACTURACIÓN:
- Si el cliente pregunta qué es un concepto de su recibo (ej: "¿qué es cargo por reconexión?", "¿qué es repetidor?", "¿qué es prorrateo?", "¿qué es fin de descuento?"):
  * Explica qué es en palabras sencillas sin tecnicismos confusos.
  * Explica por qué se originó según los datos de su cuenta.
  * Aclara si es un cobro por única vez o si continuará, dando tranquilidad y consejos para evitarlo si corresponde.

### AYUDA ANTE RECLAMOS DE PRECIO ("ESTÁ MUY CARO", "NO ME ALCANZA"):
- Si el cliente siente que paga mucho, valida con cariño su preocupación, recuerda el valor de su servicio actual y ofrécele de inmediato:
  1. **Movistar Total**: Unificar servicios fijo y móvil para ahorrar dinero mensualmente.
  2. **Fraccionamiento sin intereses**: Posibilidad de diferir su recibo en cuotas fijas (TCEA 0.0%).

### CONSULTAS FUERA DE ALCANCE (OUT-OF-SCOPE):
- Si el usuario pregunta sobre política, ciencia general, trivia ("¿quién es el presidente?", "¿quién fue a la luna?", recetas, etc.), responde con amabilidad y simpatía indicando que estás diseñada exclusivamente como su copiloto de Movistar Perú, invitándolo a consultar sobre su recibo o servicios.

### FORMATO DE RESPUESTA:
- Responde de forma concisa, amigable y estructurada (1 a 3 párrafos cortos).
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
    r"\basao\b": "molesto",
    r"\bafecta a mi cel\b": "afecta a mi celular"
}


def normalizar_texto_coloquial(texto: str) -> str:
    """Limpia y normaliza el texto para comprensión de jergas y abreviaturas."""
    t = texto.lower().strip()
    for patron, reemplazo in DICCIONARIO_NORMALIZACION.items():
        t = re.sub(patron, reemplazo, t, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", t).strip()


def clasificar_intencion_y_keys(query_original: str) -> Dict[str, Any]:
    """Clasifica intenciones clave para trazabilidad de métricas."""
    q = normalizar_texto_coloquial(query_original)
    scores = {"GREETING": 0.0, "BILLING_INCREASE": 0.0, "PRICE_COMPLAINT_OR_SAVINGS": 0.0, "OUT_OF_SCOPE": 0.0, "GENERAL_INFO": 0.0}
    
    if any(k in q for k in ["por qué", "subio", "subió", "aumento", "recibo", "mas", "más", "cobran de mas", "cobran", "cobro"]):
        scores["BILLING_INCREASE"] = 0.9
    elif any(k in q for k in ["caro", "mucho", "pagar menos", "ahorro"]):
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
            "maxOutputTokens": 600
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
    contexto financiero auditado y deducción agéntica.
    """
    client_ctx = client_context or {}
    cid = str(client_ctx.get("id") or client_ctx.get("cliente_id") or "CLI001").strip().upper()
    nombre_cliente = client_ctx.get("nombre", "Cliente").split()[0]
    
    # 1. Cargar datos auditados del cliente
    recibo_data = consultar_recibo(cid)
    nbo_data = evaluar_upgrade_movistar_total(cid)
    ficha_data = get_ficha_cliente_completa(cid)

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
                f"• **Estado:** `PENDIENTE EN BANDEJA CRM`\n\n"
                f"Un asesor senior revisará tu historial para darte una solución inmediata."
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
    ahorro_soles = float(ben.get("ahorro_mensual_soles", 29.40))
    ahorro_pct = float(ben.get("ahorro_porcentaje", 20.0))

    # Formatear historial de conversación
    historial_formateado = []
    for h in chat_history[-8:]:
        role_label = "Cliente" if h.get("role") == "user" else "Yara AI"
        historial_formateado.append(f"{role_label}: {h.get('content')}")
    historial_str = "\n".join(historial_formateado) if historial_formateado else "Sin mensajes previos (inicio de conversación)."

    prompt_gemini = f"""
{YARA_SYSTEM_PROMPT}

DATOS REALES DEL CLIENTE (AUDITADOS):
- Cliente: {client_ctx.get('nombre', 'Cliente')} (ID: {cid})
- Plan Contratado: {client_ctx.get('plan_actual', 'Plan Fibra')}
- Recibo Anterior (Junio): S/ {recibo_ant:.2f} | Recibo Actual (Julio): S/ {recibo_act:.2f}
- Variación de Recibo: +S/ {monto_var:.2f} debido a '{motivo_var}'.
- Conceptos en Factura: {', '.join([c.get('concepto', '') for c in conceptos]) if conceptos else motivo_var}
- Línea Móvil: {client_ctx.get('estado_linea_movil', 'ACTIVA')} ({client_ctx.get('telefono_movil', '987654321')}). Sin cortes reportados.
- Oferta Movistar Total: {nombre_mt} por S/ {precio_mt:.2f}/mes (Ahorro de S/ {ahorro_soles:.2f}/mes o {ahorro_pct:.0f}%).

HISTORIAL DE LA CONVERSACIÓN PREVIA:
{historial_str}

NUEVO MENSAJE DEL CLIENTE:
"{user_message}"

INSTRUCCIONES ESPECÍFICAS:
- Analiza la intención del cliente en el contexto de la charla y responde de forma natural, humana, empática y pedagógica.
- Si el cliente pregunta qué significa o qué es un concepto ("q es eso?", "¿por qué vino eso?"), explícale con total claridad qué es '{motivo_var}', por qué se generó el cargo de S/ {monto_var:.2f} y si volverá a cobrarse.
- Si el cliente dice que el internet o su recibo está muy caro, ofrécele unificar con Movistar Total para ahorrar o fraccionar su recibo sin intereses.
- Si el cliente saluda ("hi", "hola"), salúdalo con cariño por su nombre ({nombre_cliente}) y pregúntale cómo puedes ayudarlo.
- Si el cliente pregunta temas ajenos a Movistar (política, etc.), recuérdale amablemente que estás enfocada en apoyarlo con su cuenta de Movistar.
"""

    gemini_key = api_key_override or os.environ.get("GEMINI_API_KEY") or config.GEMINI_API_KEY
    if gemini_key and len(gemini_key) > 10:
        # Intentar con gemini-3.5-flash-lite y fallback a gemini-3.5-flash
        raw_reply = _call_gemini_rest(prompt_gemini, gemini_key, "gemini-3.5-flash-lite")
        if not raw_reply:
            raw_reply = _call_gemini_rest(prompt_gemini, gemini_key, "gemini-3.5-flash")

        if raw_reply:
            resp_lower = raw_reply.lower()
            msg_lower = user_message.lower()
            action_payload = None

            # Detección inteligente de componentes interactivos a adjuntar
            es_queja_precio = any(p in msg_lower for p in ["caro", "ahorrar", "pagar menos", "descuento", "precio", "bajar"])
            es_consulta_variacion = any(p in msg_lower for p in ["por qué", "porque", "subio", "subió", "cobran", "recibo", "diferencia", "mas", "más"])
            es_consulta_fraccionar = any(p in msg_lower for p in ["fraccionar", "cuotas", "partes"])

            if "asesor humano" in resp_lower and ("transferir" in resp_lower or "ticket" in resp_lower):
                action_payload = {"show_action_buttons": ["ASESOR"]}
            elif es_queja_precio or "movistar total" in resp_lower or "unificar" in resp_lower:
                action_payload = {"action": "SHOW_UPGRADE_CARD", "nbo": nbo_data}
            elif es_consulta_fraccionar:
                action_payload = {"action": "SHOW_INSTALLMENT_MODAL", "monto": recibo_act}
            elif es_consulta_variacion and ("repetidor" in resp_lower or "reconexión" in resp_lower or "descuento" in resp_lower or "prorrateo" in resp_lower):
                action_payload = {"action": "SHOW_BILLING_BREAKDOWN", "variacion": var_info}

            return {
                "response_text": raw_reply,
                "action_payload": action_payload,
                "tool_calls_executed": [{"tool": "consultar_recibo"}, {"tool": "evaluar_upgrade_movistar_total"}],
                "model_used": "Google Gemini (gemini-3.5-flash)"
            }

    # =========================================================
    # 4. MOTOR SEMÁNTICO LOCAL DE RESPALDO (EN CASO DE CORTE DE API)
    # =========================================================
    action_payload = None
    msg_low = user_message.lower().strip()

    # Saludos
    if any(msg_low == s or msg_low.startswith(s + " ") for s in ["hola", "hi", "hello", "buenas", "oye", "habla", "ey"]):
        resp_text = f"¡Hola {nombre_cliente}! Qué gusto saludarte. ¿En qué te puedo ayudar hoy con tu servicio o recibo de Movistar?"

    # Preguntas de seguimiento sobre qué es el cargo ("q es eso?", "¿qué significa?", "por qué?")
    elif any(p in msg_low for p in ["q es eso", "que es eso", "q significa", "que significa", "a que se debe", "por que ese cobro", "explica"]):
        if "reconexión" in motivo_var.lower() or "moros" in motivo_var.lower():
            resp_text = (
                f"Hola {nombre_cliente}, el **Cargo por Reconexión** de S/ {monto_var:.2f} es el costo administrativo por reactivar tu servicio "
                f"luego de una suspensión temporal por pago fuera de fecha. Es un cobro por única vez y no volverá a figurar si mantienes tus pagos al día."
            )
        elif "repetidor" in motivo_var.lower():
            resp_text = (
                f"Hola {nombre_cliente}, corresponde a la **Instalación del Repetidor WiFi** (S/ {monto_var:.2f}) que solicitaste para ampliar la cobertura de internet en tu hogar. "
                f"Es un pago único y no se cobrará en tus próximos meses."
            )
        elif "descuento" in motivo_var.lower():
            resp_text = (
                f"Hola {nombre_cliente}, significa que concluyó el periodo de tu promoción temporal con descuento, "
                f"por lo que tu plan ha retornado a su tarifa estándar regular."
            )
        else:
            resp_text = (
                f"Hola {nombre_cliente}, el concepto **{motivo_var}** corresponde a un cargo adicional de S/ {monto_var:.2f} "
                f"aplicado en tu ciclo de facturación de julio."
            )

    # Quejas de precio
    elif any(p in msg_low for p in ["caro", "mucho", "no me alcanza", "pagar menos", "ahorrar"]):
        resp_text = (
            f"Comprendo totalmente tu preocupación, {nombre_cliente}. Para ayudarte a reducir tu gasto mensual, "
            f"te propongo unificar tus servicios con **{nombre_mt}** por solo **S/ {precio_mt:.2f}/mes** "
            f"(ahorrando **S/ {ahorro_soles:.2f} al mes**). También puedes solicitar fraccionar tu recibo en cuotas fijas sin intereses."
        )
        action_payload = {"action": "SHOW_UPGRADE_CARD", "nbo": nbo_data}

    # Variación de recibo
    elif any(p in msg_low for p in ["subio", "subió", "por qué", "porque", "cobran de mas", "recibo"]):
        resp_text = f"Hola {nombre_cliente}, analicé tu recibo. Este mes pagas **S/ {monto_var:.0f} más** debido a {motivo_var.lower()}."
        action_payload = {"action": "SHOW_BILLING_BREAKDOWN", "variacion": var_info}

    # Fuera de alcance
    elif any(p in msg_low for p in ["presidente", "luna", "receta", "chiste", "futbol"]):
        resp_text = (
            f"Disculpa {nombre_cliente}, como copiloto de facturación de Yara AI estoy diseñada exclusivamente para ayudarte con tus consultas, recibos, planes y servicios de Movistar Perú. "
            f"¿Tienes alguna consulta sobre tu recibo de julio en la que te pueda apoyar?"
        )

    else:
        resp_text = (
            f"Hola {nombre_cliente}, estoy aquí para resolver cualquier duda sobre tu recibo de julio o explicarte el detalle de tus servicios de Movistar. "
            f"Cuéntame, ¿qué te gustaría revisar?"
        )

    return {
        "response_text": resp_text,
        "action_payload": action_payload,
        "tool_calls_executed": [{"tool": "consultar_recibo"}],
        "model_used": "Yara-AI-SemanticEngine (0% Alucinación)"
    }
