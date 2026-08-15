"""
state_manager.py - Gestor de Estado de Sesión y Memoria Conversacional Multi-Usuario (Streamlit)
Permite persistir chats individuales por cliente, gestionar roles y tickets de escalamiento.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import streamlit as st


# Catálogo de Clientes de Demostración con perfiles representativos
CLIENTES_CATALOGO = {
    "CLI001": {
        "id": "CLI001",
        "nombre": "Juan Pérez",
        "servicio": "Fibra 600 Mbps + Móvil 65GB",
        "plan_actual": "Plan Dúo Fibra 600 Mbps + 1 Línea Móvil",
        "tipo_servicio": "HOGAR_Y_MOVIL",
        "telefono_movil": "987654321",
        "estado_linea_movil": "ACTIVA",
        "recibo_anterior": 89.90,
        "recibo_actual": 119.90,
        "diferencia": 30.00,
        "motivo_principal": "Instalación de repetidor WiFi",
        "detalle_variacion": "Cargo único de S/ 30.00 por instalación de repetidor Smart WiFi solicitado en Junio.",
        "antiguedad": "18 meses",
        "region": "Lima - San Isidro",
        "lineas_moviles_activas": 1
    },
    "1000001": {
        "id": "1000001",
        "nombre": "Carlos Mendoza",
        "servicio": "Fibra Óptica 500 Mbps Pro",
        "plan_actual": "Trío Clásico 100 Mbps",
        "tipo_servicio": "SOLO_HOGAR",
        "telefono_movil": "981234567",
        "estado_linea_movil": "SIN_MOVIL_ASOCIADO",
        "recibo_anterior": 129.90,
        "recibo_actual": 139.90,
        "diferencia": 10.00,
        "motivo_principal": "Fin de promoción de descuento",
        "detalle_variacion": "Vencimiento del 10% de descuento comercial aplicado durante 6 meses.",
        "antiguedad": "24 meses",
        "region": "Lima - Miraflores",
        "lineas_moviles_activas": 0
    },
    "CLI002": {
        "id": "CLI002",
        "nombre": "María Torres",
        "servicio": "Plan Fibra 1000 Mbps",
        "plan_actual": "Plan Fibra Gamer 1000 Mbps",
        "tipo_servicio": "SOLO_HOGAR",
        "telefono_movil": "993456789",
        "estado_linea_movil": "ACTIVA",
        "recibo_anterior": 149.90,
        "recibo_actual": 179.90,
        "diferencia": 30.00,
        "motivo_principal": "Fin de descuento de bienvenida",
        "detalle_variacion": "Culminación de descuento promocional de bienvenida de S/ 30.00.",
        "antiguedad": "7 meses",
        "region": "Lima - Surco",
        "lineas_moviles_activas": 2
    },
    "CLI004": {
        "id": "CLI004",
        "nombre": "Lucía Ramos",
        "servicio": "Plan Fibra 300 Mbps",
        "plan_actual": "Dúo Internet 300 Mbps + Fijo",
        "tipo_servicio": "HOGAR",
        "telefono_movil": "976543210",
        "estado_linea_movil": "ACTIVA",
        "recibo_anterior": 69.90,
        "recibo_actual": 94.90,
        "diferencia": 25.00,
        "motivo_principal": "Prorrateo por alta a mitad de ciclo",
        "detalle_variacion": "Cobro de días proporcionales por activación el día 12 del ciclo de facturación.",
        "antiguedad": "1 mes",
        "region": "Arequipa",
        "lineas_moviles_activas": 1
    },
    "CLI005": {
        "id": "CLI005",
        "nombre": "Roberto Díaz",
        "servicio": "Plan Móvil 65GB Ilimitado",
        "plan_actual": "Plan Móvil Ilimitado 65GB",
        "tipo_servicio": "MOVIL",
        "telefono_movil": "965432109",
        "estado_linea_movil": "ACTIVA",
        "recibo_anterior": 55.90,
        "recibo_actual": 90.90,
        "diferencia": 35.00,
        "motivo_principal": "Cuota 3/12 de equipo financiado",
        "detalle_variacion": "Cuota mensual por adquisición financiada de smartphone Samsung Galaxy.",
        "antiguedad": "14 meses",
        "region": "Trujillo",
        "lineas_moviles_activas": 1
    },
    "CLI006": {
        "id": "CLI006",
        "nombre": "Ana Castro",
        "servicio": "Plan Dúo Básico",
        "plan_actual": "Dúo Básico 100 Mbps",
        "tipo_servicio": "HOGAR",
        "telefono_movil": "954321098",
        "estado_linea_movil": "SUSPENDIDA_POR_PAGO",
        "recibo_anterior": 79.90,
        "recibo_actual": 90.40,
        "diferencia": 10.50,
        "motivo_principal": "Cargo por reconexión morosa (OC1_RECONEXION)",
        "detalle_variacion": "Cargo por rehabilitación tras suspensión temporal del servicio por pago fuera de fecha.",
        "antiguedad": "9 meses",
        "region": "Chiclayo",
        "lineas_moviles_activas": 1
    }
}


def init_session_state():
    """Inicializa todas las variables de st.session_state con persistencia y memoria conversacional."""
    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "landing"

    if "user_role" not in st.session_state:
        st.session_state.user_role = "cliente"

    if "active_client_id" not in st.session_state:
        st.session_state.active_client_id = "CLI001"

    # Diccionario de memorias de chat indexado por ID de cliente
    if "client_chat_memories" not in st.session_state:
        st.session_state.client_chat_memories = {}

    # Historial de conversación activo (inicia vacío para nuevo chat)
    if "chat_history" not in st.session_state:
        cur_id = st.session_state.active_client_id
        st.session_state.chat_history = list(st.session_state.client_chat_memories.get(cur_id, []))

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

    if "selected_ticket_id" not in st.session_state:
        st.session_state.selected_ticket_id = "TCK-1001"

    if "selected_solution_tab" not in st.session_state:
        st.session_state.selected_solution_tab = "fraccionamiento"

    if "selected_cuotas" not in st.session_state:
        st.session_state.selected_cuotas = 3


def switch_active_client(new_client_id: str):
    """Cambia el cliente activo guardando y restaurando su memoria conversacional individual."""
    old_id = st.session_state.get("active_client_id", "CLI001")
    if "client_chat_memories" not in st.session_state:
        st.session_state.client_chat_memories = {}
        
    # Guardar memoria del cliente anterior
    st.session_state.client_chat_memories[old_id] = list(st.session_state.get("chat_history", []))
    
    # Cambiar al nuevo cliente
    st.session_state.active_client_id = new_client_id
    
    # Restaurar memoria del nuevo cliente o iniciar vacía si es nuevo
    st.session_state.chat_history = list(st.session_state.client_chat_memories.get(new_client_id, []))


def add_chat_message(role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
    """Agrega un mensaje al historial de chat de la sesión y sincroniza la memoria del cliente."""
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
    
    # Sincronizar memoria del cliente
    cur_id = st.session_state.get("active_client_id", "CLI001")
    if "client_chat_memories" not in st.session_state:
        st.session_state.client_chat_memories = {}
    st.session_state.client_chat_memories[cur_id] = list(st.session_state.chat_history)


def reset_chat():
    """Reinicia la conversación del cliente actual dejándola completamente limpia."""
    st.session_state.chat_history = []
    cur_id = st.session_state.get("active_client_id", "CLI001")
    if "client_chat_memories" in st.session_state:
        st.session_state.client_chat_memories[cur_id] = []


def escalate_case_to_human(client_id: str, client_name: str, reason: str) -> str:
    """Transfiere el caso actual a la cola de derivaciones para atención humana."""
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
