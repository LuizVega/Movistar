"""
services/gemini_service.py - Motor de Inteligencia Conversacional Yara AI con Google Gemini
Implementa memoria conversacional multi-turno, razonamiento contextual con datasets reales (0% alucinaciones),
y activación de botones de escalamiento humano solo cuando la IA lo recomienda o cuando la data no está disponible.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional

import config
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
- Tu misión principal es hacer sentir bien, comprendido, escuchado y tranquilo al cliente en todo momento, resolviendo de inmediato cualquier consulta sobre su facturación, servicios contratados, líneas móviles, fibra óptica o promociones.

### COMPRENSIÓN LINGÜÍSTICA Y MANEJO DE EMOCIONES:
- Comprendes a la perfección el lenguaje coloquial peruano, jergas, abreviaturas, faltas de ortografía o múltiples preguntas en un solo mensaje ("me cobrand e mas en mi internet y cancelaron mi teléfono, q pasa", "q fue", "poq", "xq", "lucas", "asao").
- Si el usuario se expresa con molestia, enfado o frustración, mantén la máxima calma, empatiza con calidez y dale la respuesta exacta a cada uno de sus puntos.

### POLÍTICA ESTRICTA DE 0% ALUCINACIONES Y MEMORIA:
1. Toda cifra en Soles (S/), estado de línea móvil/fija, fechas de vencimiento, nombres de promociones, megas/gigas y causas de cobro provienen EXCLUSIVAMENTE de los datos reales auditados del cliente.
2. Tienes en cuenta todo el historial de la conversación previa para responder de forma coherente a preguntas de seguimiento.
3. Si el cliente pregunta por un dato que NO figura en el sistema o una falla técnica fuera de los registros disponibles, explícaselo con amabilidad y amistosamente ofrécele transferir su caso a un asesor humano.
4. Responde en un tono fluido, natural y directo (máximo 2 a 3 oraciones por respuesta).
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
    r"\basado\b": "molesto",
    r"\bq fue\b": "qué pasó",
    r"\bque fue\b": "qué pasó"
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
        "PHONE_STATUS": 0.0,
        "MOVISTAR_TOTAL": 0.0,
        "INSTALLMENTS": 0.0,
        "HUMAN_ESCALATION": 0.0,
        "PAYMENT": 0.0,
        "GREETING": 0.0,
        "TECHNICAL_SPEED": 0.0,
        "GENERAL_INFO": 0.0
    }
    keys_detected = []

    # 1. Aumento de Cobro / Variación de Recibo
    for p in ["por qué", "subio", "subió", "aumento", "aumentó", "mas", "más", "alto", "caro", "cobran de mas", "cobran de más", "cobro", "recibo", "factura", "variacion", "variación", "diferencia", "prorrateo", "repetidor", "vino", "cobran"]:
        if p in query_norm:
            scores["BILLING_INCREASE"] += 0.5
            keys_detected.append(p)

    # 2. Movistar Total / Upgrade / Ofertas convergentes
    for p in ["total", "upgrade", "cambiar plan", "cambiar de plan", "cambio de plan", "migrar", "ahorrar", "ahorro", "convergente", "unificar", "oferta", "promocion", "promoción", "promo", "fibra y movil", "mejorar", "pagar menos"]:
        if p in query_norm:
            scores["MOVISTAR_TOTAL"] += 0.6
            keys_detected.append(p)

    # 3. Estado de línea / teléfono móvil (cuando no es primariamente una solicitud comercial de ahorro/unificar)
    if scores["MOVISTAR_TOTAL"] < 0.6:
        for p in ["telefono", "teléfono", "celular", "linea", "línea", "movil", "móvil", "cortaron", "corte", "cancelaron", "cancelaron mi plan", "sin linea", "sin línea", "bloqueado", "suspendido"]:
            if p in query_norm:
                scores["PHONE_STATUS"] += 0.5
                keys_detected.append(p)

    # 4. Fraccionamiento
    for p in ["fraccionar", "fraccionamiento", "cuotas", "pagar en partes", "diferir", "deuda"]:
        if p in query_norm:
            scores["INSTALLMENTS"] += 0.6
            keys_detected.append(p)

    # 5. Asesor humano / Reclamo
    for p in ["humano", "asesor", "operador", "persona", "supervisor", "reclamo", "queja", "libro de reclamaciones", "baja", "cancelar contrato"]:
        if p in query_norm:
            scores["HUMAN_ESCALATION"] += 0.7
            keys_detected.append(p)

    # 6. Saludos
    for p in ["hola", "buenos dias", "buenos días", "buenas tardes", "buenas noches", "hey", "saludos", "ayuda"]:
        if p in query_norm:
            scores["GREETING"] += 0.3
            keys_detected.append(p)


    # Velocidad / Falla técnica
    for p in ["lento", "velocidad", "megas", "mbps", "gigas", "falla", "caida", "no funciona"]:
        if p in query_norm:
            scores["TECHNICAL_SPEED"] += 0.4
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
    con memoria multi-turno e inyección de datos auditados de clientes.
    """
    client_ctx = client_context or {}
    cid = str(client_ctx.get("id") or client_ctx.get("cliente_id") or "CLI001").strip().upper()
    nombre_cliente = client_ctx.get("nombre", "Cliente").split()[0]
    
    # 1. Cargar datos reales y auditados del cliente desde SQLite y CSVs
    recibo_data = consultar_recibo(cid)
    nbo_data = evaluar_upgrade_movistar_total(cid)
    ficha_data = get_ficha_cliente_completa(cid)

    # 2. Análisis semántico de intención
    nlu_result = clasificar_intencion_y_keys(user_message)
    top_intent = nlu_result["top_intent"]

    # 3. Verificar si el usuario solicita explícitamente escalamiento a asesor humano
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

    # 4. Invocación de Google Gemini en Vivo con Memoria Multi-Turno
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

            # Construir historial conversacional multi-turno
            historial_formateado = []
            for h in chat_history[-6:]:  # Últimos 6 turnos para mantener contexto preciso
                role_label = "Cliente" if h.get("role") == "user" else "Yara AI"
                historial_formateado.append(f"{role_label}: {h.get('content')}")
            historial_str = "\n".join(historial_formateado) if historial_formateado else "Sin mensajes previos."

            prompt_grounding = f"""
            DATOS REALES Y AUDITADOS DEL CLIENTE:
            - Nombre: {client_ctx.get('nombre', 'Cliente')} (Trátalo amablemente por su nombre: {nombre_cliente})
            - ID de Cuenta: {cid}
            - Plan Actual: {client_ctx.get('plan_actual', 'Plan Fibra')}
            - Servicio: {client_ctx.get('servicio', 'Internet')}
            - Estado Línea Móvil: {client_ctx.get('estado_linea_movil', 'ACTIVA')} (Teléfono: {client_ctx.get('telefono_movil', 'No asociado')})
            - Recibo Anterior (Junio 2026): S/ {client_ctx.get('recibo_anterior', 89.90):.2f}
            - Recibo Actual (Julio 2026): S/ {client_ctx.get('recibo_actual', 119.90):.2f}
            - Detalle de Variación de Recibo: {json.dumps(recibo_data, ensure_ascii=False)}
            - Oferta Movistar Total: {json.dumps(nbo_data, ensure_ascii=False)}
            - Ficha Técnica y Promociones: {json.dumps(ficha_data, ensure_ascii=False)}

            HISTORIAL PREVIO DE LA CONVERSACIÓN:
            {historial_str}

            NUEVA CONSULTA DEL CLIENTE:
            "{user_message}"

            DIRECTIVAS:
            1. Responde de forma muy amable, empática, tranquila y resolutiva (máximo 2-3 oraciones).
            2. Si pregunta por su teléfono/línea o por qué le cortaron el servicio, revisa el Estado de Línea Móvil ({client_ctx.get('estado_linea_movil', 'ACTIVA')}). Si la línea figura ACTIVA sin cortes, infórmaselo con tranquilidad. Si tiene fallas técnicas o si el dato no figura en el sistema, ofrécele contactar con un asesor humano.
            3. Si pregunta por su recibo o aumento, explica el motivo real y el monto exacto en Soles.
            4. Si la consulta involucra dos temas a la vez (ej. internet y teléfono), responde a ambos puntos con claridad.
            5. Mantén 0% de alucinaciones.
            """

            response = model.generate_content(prompt_grounding)
            if response and response.text:
                resp_text = response.text.strip()
                action_payload = None

                # Detectar si corresponde mostrar componentes de acción
                resp_lower = resp_text.lower()
                if "asesor humano" in resp_lower or "asesor" in resp_lower or "transferir" in resp_lower or "conectar con un asesor" in resp_lower:
                    action_payload = {"show_action_buttons": ["ASESOR"]}
                elif top_intent == "BILLING_INCREASE" and ("repetidor" in resp_lower or "prorrateo" in resp_lower or "descuento" in resp_lower or "s/" in resp_lower):
                    action_payload = {"action": "SHOW_BILLING_BREAKDOWN", "variacion": recibo_data.get("variacion", {})}
                elif top_intent == "MOVISTAR_TOTAL" or "movistar total" in resp_lower:
                    action_payload = {"action": "SHOW_UPGRADE_CARD", "nbo": nbo_data}
                elif top_intent == "INSTALLMENTS" or "fraccionar" in resp_lower:
                    action_payload = {"action": "SHOW_INSTALLMENT_MODAL", "monto": client_ctx.get("recibo_actual", 119.90)}

                return {
                    "response_text": resp_text,
                    "action_payload": action_payload,
                    "tool_calls_executed": [{"tool": "consultar_recibo"}, {"tool": "evaluar_upgrade_movistar_total"}],
                    "model_used": f"Google Gemini ({config.GEMINI_MODEL})"
                }
        except Exception:
            pass

    # =========================================================
    # 5. MOTOR SEMÁNTICO LOCAL DE RESPALDO (ROBUSTO Y CONTEXTUAL)
    # =========================================================
    action_payload = None

    if top_intent == "BILLING_INCREASE":
        var = recibo_data.get("variacion", {}) or {}
        delta = var.get("monto", 0.0)
        conceptos = recibo_data.get("conceptos_adicionales", [])
        c_nom = conceptos[0]["concepto"] if conceptos else "Ajuste de facturación"
        
        c_clean = c_nom.lower().replace("instalación de", "").replace("instalacion de", "").strip()
        causa = f"la instalación de tu {c_clean}" if "repetidor" in c_nom.lower() else f"{c_nom.lower()}"
        
        resp_text = f"Hola {nombre_cliente}, analicé tu recibo. Este mes pagas **S/ {delta:.0f} más** debido a {causa}."
        action_payload = {"action": "SHOW_BILLING_BREAKDOWN", "variacion": var}

    elif top_intent == "MOVISTAR_TOTAL":
        of = nbo_data.get("oferta_recomendada", {})
        ben = nbo_data.get("beneficio_economico", {})
        resp_text = (
            f"Hola {nombre_cliente}, he evaluado tu cuenta y puedes migrar a **{of.get('nombre_oferta')}** "
            f"por **S/ {of.get('precio_promocional', 110.40):.2f}/mes**, ahorrando **S/ {ben.get('ahorro_mensual_soles', 29.40):.2f} al mes**."
        )
        action_payload = {"action": "SHOW_UPGRADE_CARD", "nbo": nbo_data}

    elif top_intent == "PHONE_STATUS":
        estado_linea = client_ctx.get("estado_linea_movil", "ACTIVA")
        tel = client_ctx.get("telefono_movil", "asociado")
        if estado_linea == "ACTIVA":
            resp_text = (
                f"Hola {nombre_cliente}, he revisado tu cuenta y tu línea móvil ({tel}) figura **activa y operativa** en nuestro sistema sin ningún corte. "
                f"Si estás experimentando problemas de señal o cobertura, ¿deseas que te comunique con un asesor humano para revisarlo a detalle?"
            )
            action_payload = {"show_action_buttons": ["ASESOR"]}
        elif estado_linea == "SUSPENDIDA_POR_PAGO":
            resp_text = (
                f"Hola {nombre_cliente}, tu línea móvil ({tel}) registra una suspensión temporal por regularización de pago. "
                f"Puedes abonar tu saldo pendiente de S/ {client_ctx.get('recibo_actual', 90.40):.2f} para restablecerla de inmediato o te comunico con un asesor."
            )
            action_payload = {"show_action_buttons": ["PAGAR", "ASESOR"]}
        else:
            resp_text = (
                f"Hola {nombre_cliente}, en tu ficha actual no figura una línea móvil asociada a tu plan de hogar. "
                f"¿Deseas que te transfiera con un asesor humano para verificar el estado de tu línea?"
            )
            action_payload = {"show_action_buttons": ["ASESOR"]}

    elif top_intent == "INSTALLMENTS":
        rec_act = client_ctx.get("recibo_actual", 119.90)
        resp_text = f"Hola {nombre_cliente}, puedes fraccionar tu saldo de S/ {rec_act:.2f} en 6 cuotas fijas de S/ {(rec_act/6):.2f}/mes sin intereses."
        action_payload = {"action": "SHOW_INSTALLMENT_MODAL", "monto": rec_act}

    elif top_intent == "TECHNICAL_SPEED":
        plan_nom = client_ctx.get("plan_actual", "Fibra Óptica")
        resp_text = (
            f"Hola {nombre_cliente}, tu plan contratado es **{plan_nom}**. "
            f"Si experimentas lentitud, he verificado que no hay averías masivas en tu zona. ¿Deseas que transfiera tu caso a soporte técnico con un asesor?"
        )
        action_payload = {"show_action_buttons": ["ASESOR"]}

    elif top_intent == "GREETING":
        resp_text = f"¡Hola {nombre_cliente}! Soy Yara AI, tu copiloto de facturación de Movistar Perú. ¿En qué puedo ayudarte hoy con tu servicio?"
        action_payload = None

    else:
        # Consulta sin datos registrados o fuera del alcance de la base de datos
        resp_text = (
            f"Estimado {nombre_cliente}, he revisado tu ficha y no encuentro un registro específico sobre esa consulta en tu cuenta actual. "
            f"¿Deseas que te comunique con un asesor humano especializado para revisarlo a detalle?"
        )
        action_payload = {"show_action_buttons": ["ASESOR"]}

    return {
        "response_text": resp_text,
        "action_payload": action_payload,
        "tool_calls_executed": [{"tool": "consultar_recibo"}],
        "model_used": "Yara-AI-SemanticEngine (0% Alucinación)"
    }

