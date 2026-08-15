"""
state_manager.py - Gestor de Estado Global de Sesión para Streamlit (Movistar)
Soporta persistencia y alternancia fluida entre 'Modo Cliente' y 'Modo Trabajador / Asesor'.
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Any, List, Optional


# Clientes precargados de referencia
CLIENTES_CATALOGO = {
    "CLI001": {
        "id": "CLI001",
        "nombre": "Juan Pérez",
        "servicio": "Plan Fibra 600 Mbps + Móvil",
        "telefono": "987-654-321",
        "periodo": "2026-07",
        "recibo_actual": 119.90,
        "recibo_anterior": 89.90,
        "estado_linea": "Activa - Al día"
    },
    "1000001": {
        "id": "1000001",
        "nombre": "Carlos Mendoza",
        "servicio": "Fibra Óptica 500 Mbps Pro",
        "telefono": "991-234-567",
        "periodo": "2026-07",
        "recibo_actual": 111.90,
        "recibo_anterior": 111.90,
        "estado_linea": "Activa - Elegible Movistar Total"
    },
    "CLI002": {
        "id": "CLI002",
        "nombre": "María Torres",
        "servicio": "Plan Fibra 1000 Mbps",
        "telefono": "976-543-210",
        "periodo": "2026-07",
        "recibo_actual": 129.90,
        "recibo_anterior": 109.90,
        "estado_linea": "Activa - Fin Descuento"
    },
    "CLI004": {
        "id": "CLI004",
        "nombre": "Lucía Ramos",
        "servicio": "Plan Fibra 300 Mbps",
        "telefono": "955-432-109",
        "periodo": "2026-07",
        "recibo_actual": 104.90,
        "recibo_anterior": 79.90,
        "estado_linea": "Activa - Prorrateo Alta"
    },
    "CLI005": {
        "id": "CLI005",
        "nombre": "Roberto Díaz",
        "servicio": "Plan Móvil Ilimitado 65GB",
        "telefono": "944-321-098",
        "periodo": "2026-07",
        "recibo_actual": 94.90,
        "recibo_anterior": 59.90,
        "estado_linea": "Activa - Cuota Equipo ShEq"
    },
    "CLI006": {
        "id": "CLI006",
        "nombre": "Ana Castro",
        "servicio": "Plan Dúo Básico",
        "telefono": "933-210-987",
        "periodo": "2026-07",
        "recibo_actual": 75.50,
        "recibo_anterior": 65.00,
        "estado_linea": "Activa - Reconexión"
    }
}


def init_session_state():
    """
    Garantiza la inicialización de todas las variables globales de sesión
    para persistir datos al alternar entre roles o ejecutar re-renders de Streamlit.
    """
    # 0. Modo de vista inicial: 'landing' | 'cliente' | 'trabajador'
    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "landing"

    # 1. Rol de usuario: 'cliente' | 'trabajador'
    if "user_role" not in st.session_state:
        st.session_state.user_role = "cliente"

    # 2. ID del cliente activo en la sesión
    if "active_client_id" not in st.session_state:
        st.session_state.active_client_id = "CLI001"


    # 3. Historial de conversación del Asistente Digital (inicia vacío esperando la consulta del usuario)
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # 4. Cola de tickets escalados a asesor humano
    if "escalated_tickets" not in st.session_state:
        st.session_state.escalated_tickets = [
            {
                "ticket_id": "TCK-1001",
                "client_id": "CLI004",
                "client_name": "Lucía Ramos",
                "reason": "Discrepancia en cargo proporcional de prorrateo por cambio de plan.",
                "chat_history": [
                    {"role": "user", "content": "¿Por qué mi recibo vino con S/ 25.00 de más?"},
                    {"role": "assistant", "content": "Se debe al prorrateo de días por la activación de tu plan en medio del ciclo."},
                    {"role": "user", "content": "Quiero que un asesor revise si aplica nota de crédito."}
                ],
                "timestamp": "2026-08-14 00:15:30",
                "status": "PENDIENTE",
                "priority": "MEDIA",
                "assigned_agent": "Sin Asignar",
                "notes": "Cliente solicita revisión de días facturados en alta."
            },
            {
                "ticket_id": "TCK-1002",
                "client_id": "CLI006",
                "client_name": "Ana Castro",
                "reason": "Solicitud de exoneración de cargo por reconexión morosa.",
                "chat_history": [
                    {"role": "user", "content": "Pagué ayer y me cobran reconexión de S/ 10.50."},
                    {"role": "assistant", "content": "El cargo OC1_RECONEXION corresponde al corte del servicio."},
                    {"role": "user", "content": "Deseo hablar con un asesor para fraccionar o exonerar."}
                ],
                "timestamp": "2026-08-14 00:22:10",
                "status": "EN_ATENCION",
                "priority": "ALTA",
                "assigned_agent": "Carlos Vega (Asesor Senior)",
                "notes": "En evaluación de fidelización por antigüedad."
            }
        ]

    # 5. Ticket seleccionado en la vista de trabajador
    if "selected_ticket_id" not in st.session_state:
        st.session_state.selected_ticket_id = "TCK-1001"

    # 6. Estado de la solución comercial seleccionada en cliente ('fraccionamiento' | 'movistar_total')
    if "selected_solution_tab" not in st.session_state:
        st.session_state.selected_solution_tab = "fraccionamiento"

    # 7. Cuotas de fraccionamiento seleccionadas (3, 6, 12)
    if "selected_cuotas" not in st.session_state:
        st.session_state.selected_cuotas = 3


def add_chat_message(role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
    """Agrega un mensaje al historial de chat de la sesión."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    meta = metadata or {}
    if "timestamp" not in meta:
        meta["timestamp"] = datetime.now().strftime("%H:%M")

    st.session_state.chat_history.append({
        "role": role,
        "content": content,
        "metadata": meta
    })


def reset_chat():
    """Reinicia la conversación actual dejándola completamente limpia para iniciar un nuevo chat."""
    st.session_state.chat_history = []



def escalate_case_to_human(client_id: str, client_name: str, reason: str) -> str:

    """
    Transfiere el caso actual a la cola de derivaciones para atención humana.
    Retorna el ticket_id generado.
    """
    if "escalated_tickets" not in st.session_state:
        st.session_state.escalated_tickets = []

    nuevo_num = len(st.session_state.escalated_tickets) + 1001
    ticket_id = f"TCK-{nuevo_num}"
    
    chat_snapshot = list(st.session_state.get("chat_history", []))

    nuevo_ticket = {
        "ticket_id": ticket_id,
        "client_id": client_id,
        "client_name": client_name,
        "reason": reason,
        "chat_history": chat_snapshot,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "PENDIENTE",
        "priority": "ALTA",
        "assigned_agent": "Cola General",
        "notes": "Derivado automáticamente desde Asistente Digital con contexto completo."
    }

    # Insertar al inicio de la cola
    st.session_state.escalated_tickets.insert(0, nuevo_ticket)
    st.session_state.selected_ticket_id = ticket_id

    return ticket_id


def update_ticket_status(ticket_id: str, new_status: str, notes: Optional[str] = None, agent: Optional[str] = None):
    """Actualiza el estado y notas de un ticket en la cola de derivaciones."""
    tickets = st.session_state.get("escalated_tickets", [])
    for t in tickets:
        if t["ticket_id"] == ticket_id:
            t["status"] = new_status
            if notes is not None:
                t["notes"] = notes
            if agent is not None:
                t["assigned_agent"] = agent
            break


def get_active_client_data() -> Dict[str, Any]:
    """Retorna los datos del cliente activo en la sesión."""
    cid = st.session_state.get("active_client_id", "CLI001")
    return CLIENTES_CATALOGO.get(cid, CLIENTES_CATALOGO["CLI001"])
