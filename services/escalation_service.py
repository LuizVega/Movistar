"""
services/escalation_service.py - Servicio de Escalamiento y Derivación a Asesor Humano (Movistar)
Gestiona disparadores explícitos y automáticos (reclamos graves, solicitud de baja, reintentos fallidos)
generando resúmenes concisos e insertando tickets en st.session_state.escalated_tickets.
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from state_manager import CLIENTES_CATALOGO


# Palabras clave para escalamiento explícito
KEYWORDS_EXPLICITAS = [
    "hablar con una persona", "asesor humano", "operador", "ejecutivo",
    "persona real", "agente humano", "comunicarme con un asesor",
    "atencion humana", "atención humana", "hablar con alguien",
    "pasar con un asesor", "transferir", "comunicar con un asesor",
    "hablar con un asesor", "quiero un asesor", "humano", "operadora"
]

# Palabras clave para reclamos graves o solicitud de baja (escalamiento automático)
KEYWORDS_RECLAMOS_GRAVES = [
    "dar de baja", "cancelar mi servicio", "cancelar contrato", "anular servicio",
    "baja del servicio", "renunciar", "indecopi", "osiptel", "libro de reclamaciones",
    "denuncia", "estafa", "robo", "cobro indebido", "fraude", "abuso", "demanda"
]

# Palabras clave de frustración o no resolución
KEYWORDS_FRUSTRACION = [
    "no me ayudas", "no entiendes", "no me sirve", "no responde mi pregunta",
    "sigues sin responder", "inútil", "inutil", "no es lo que pregunté"
]


def generar_resumen_problema(chat_history: List[Dict[str, Any]], motivo_detectado: str) -> str:
    """
    Genera un resumen conciso en 2-3 líneas del problema del cliente
    a partir del historial de conversación y motivo.
    """
    mensajes_usuario = [m.get("content", "") for m in chat_history if m.get("role") == "user"]
    ultimas_consultas = " | ".join(mensajes_usuario[-3:]) if mensajes_usuario else "Sin consultas previas"
    
    resumen = (
        f"1. Motivo Principal: {motivo_detectado}.\n"
        f"2. Contexto de Interacción: El cliente manifestó dudas/disconformidad ('{ultimas_consultas[:120]}').\n"
        f"3. Acción Requerida: Asesor debe revisar historial de cobro/planes y brindar solución directa."
    )
    return resumen


def detectar_necesidad_escalamiento(user_query: str, chat_history: List[Dict[str, Any]], client_id: str) -> Tuple[bool, str, str]:
    """
    Evalúa si la consulta actual o el estado de la conversación requiere escalamiento a humano.
    Retorna: (debe_escalar: bool, tipo_disparador: str, motivo_detectado: str)
    """
    q = user_query.strip().lower()

    # 1. Disparador Explícito
    for kw in KEYWORDS_EXPLICITAS:
        if kw in q:
            return True, "EXPLÍCITO", f"Solicitud directa del cliente: '{user_query}'"

    # 2. Disparador Automático: Reclamo Grave / Solicitud de Baja
    for kw in KEYWORDS_RECLAMOS_GRAVES:
        if kw in q:
            return True, "AUTOMÁTICO_GRAVE", f"Intención crítica detectada ({kw.upper()}): '{user_query}'"

    # 3. Disparador Automático: Frustración del cliente
    for kw in KEYWORDS_FRUSTRACION:
        if kw in q:
            return True, "AUTOMÁTICO_FRUSTRACION", f"Frustración detectada en atención AI: '{user_query}'"

    # 4. Disparador Automático: 2 o más intentos no resueltos consecutivos
    # Verificamos si los últimos 2 mensajes del asistente fueron de fallback / no resolución
    mensajes_asistente = [m.get("content", "") for m in chat_history if m.get("role") == "assistant"]
    if len(mensajes_asistente) >= 2:
        ultimos_2 = mensajes_asistente[-2:]
        fallbacks = sum(1 for m in ultimos_2 if "no dispongo de ese dato" in m.lower() or "no pude encontrar" in m.lower())
        if fallbacks >= 2:
            return True, "AUTOMÁTICO_REINTENTOS", "IA no pudo resolver la consulta tras 2 intentos consecutivos."

    return False, "NINGUNO", ""


def escalar_a_humano(client_id: str, chat_history: List[Dict[str, Any]], motivo_detectado: str, prioridad: str = "ALTA") -> Dict[str, Any]:
    """
    Ejecuta el escalamiento creando el ticket con el esquema estricto en st.session_state.escalated_tickets.
    """
    if "escalated_tickets" not in st.session_state:
        st.session_state.escalated_tickets = []

    cid = str(client_id).strip().upper()
    cliente_data = CLIENTES_CATALOGO.get(cid, {
        "id": cid,
        "nombre": f"Cliente {cid}",
        "telefono": "999-000-000",
        "servicio": "Servicio Movistar"
    })
    
    nuevo_num = len(st.session_state.escalated_tickets) + 1001
    ticket_id = f"TCK-{nuevo_num}"
    
    resumen = generar_resumen_problema(chat_history, motivo_detectado)
    
    ticket = {
        "ticket_id": ticket_id,
        "client_id": cid,
        "client_name": cliente_data["nombre"],
        "reason": motivo_detectado,
        "summary": resumen,
        "chat_history": list(chat_history),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "PENDIENTE",
        "priority": prioridad,
        "assigned_agent": "Cola General CRM",
        "notes": f"Derivado automáticamente ({prioridad}). {resumen[:100]}..."
    }

    # Insertar al inicio de la cola
    st.session_state.escalated_tickets.insert(0, ticket)
    st.session_state.selected_ticket_id = ticket_id
    
    # Marcar bandera de escalamiento activo para este cliente
    if "cliente_escalado_activo" not in st.session_state:
        st.session_state.cliente_escalado_activo = {}
    st.session_state.cliente_escalado_activo[cid] = ticket_id

    return ticket


def cliente_tiene_ticket_pendiente(client_id: str) -> Optional[Dict[str, Any]]:
    """Verifica si el cliente tiene un ticket activo en estado PENDIENTE o EN_ATENCION."""
    cid = str(client_id).strip().upper()
    tickets = st.session_state.get("escalated_tickets", [])
    for t in tickets:
        if t["client_id"] == cid and t["status"] in ["PENDIENTE", "EN_ATENCION"]:
            return t
    return None
