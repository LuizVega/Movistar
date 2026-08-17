"""
state_manager.py - Gestor de Estado de Sesión y Memoria Conversacional Multi-Usuario (Streamlit)
Permite persistir chats individuales por cliente, gestionar roles y tickets de escalamiento.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import streamlit as st


# Catálogo de Clientes de Demostración con perfiles representativos y causales analíticas
CLIENTES_CATALOGO = {
    "CLI001": {
        "id": "CLI001",
        "nombre": "Juan Pérez",
        "servicio": "Fibra 600 Mbps + Móvil 65GB",
        "plan_actual": "Plan Dúo Fibra 600 Mbps + 1 Línea Móvil",
        "tipo_servicio": "HOGAR_Y_MOVIL",
        "modalidad_facturacion": "Renta Adelantada",
        "tipo_producto_b2c": "Fibra Residencial + Móvil",
        "escenario_tag": "Cargo Único Repetidor Smart WiFi",
        "telefono_movil": "987654321",
        "estado_linea_movil": "ACTIVA",
        "recibo_anterior": 89.90,
        "recibo_actual": 119.90,
        "diferencia": 30.00,
        "tipo_causa": "cargo_unico",
        "motivo_principal": "Instalación de repetidor WiFi",
        "detalle_variacion": "Cargo único de S/ 30.00 por instalación de repetidor Smart WiFi solicitado en Junio.",
        "beneficios_actuales": "600 Mbps simétricos de fibra, repetidor Smart WiFi activo y llamadas ilimitadas a todo destino.",
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
        "modalidad_facturacion": "Renta Adelantada",
        "tipo_producto_b2c": "Trío Clásico Hogar (Internet + TV + Fono)",
        "escenario_tag": "Escenario (d) Fin de Descuento Fidelización",
        "telefono_movil": "981234567",
        "estado_linea_movil": "SIN_MOVIL_ASOCIADO",
        "recibo_anterior": 129.90,
        "recibo_actual": 139.90,
        "diferencia": 10.00,
        "tipo_causa": "fin_descuento",
        "motivo_principal": "Fin de promoción de descuento",
        "detalle_variacion": "Vencimiento del 10% de descuento comercial aplicado durante 6 meses.",
        "beneficios_actuales": "Internet ilimitado para el hogar con estabilidad garantizada y soporte prioritario.",
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
        "modalidad_facturacion": "Renta Adelantada",
        "tipo_producto_b2c": "Fibra Gamer Ultra 1000 Mbps",
        "escenario_tag": "Escenario (d) Fin de Descuento Bienvenida",
        "telefono_movil": "993456789",
        "estado_linea_movil": "ACTIVA",
        "recibo_anterior": 149.90,
        "recibo_actual": 179.90,
        "diferencia": 30.00,
        "tipo_causa": "fin_descuento",
        "motivo_principal": "Fin de descuento de bienvenida",
        "detalle_variacion": "Culminación de descuento promocional de bienvenida de S/ 30.00.",
        "beneficios_actuales": "Velocidad ultra rápida de 1000 Mbps con baja latencia ideal para streaming y gaming.",
        "antiguedad": "7 meses",
        "region": "Lima - Surco",
        "lineas_moviles_activas": 2
    },
    "CLI003": {
        "id": "CLI003",
        "nombre": "Carlos Ruiz",
        "servicio": "Plan Fibra 400 Mbps",
        "plan_actual": "Plan Fibra 400 Mbps",
        "tipo_servicio": "HOGAR",
        "modalidad_facturacion": "Renta Adelantada",
        "tipo_producto_b2c": "Fibra Simétrica 400 Mbps",
        "escenario_tag": "Recibo Regular Sin Variación",
        "telefono_movil": "945678123",
        "estado_linea_movil": "ACTIVA",
        "recibo_anterior": 69.90,
        "recibo_actual": 69.90,
        "diferencia": 0.00,
        "tipo_causa": "sin_variacion",
        "motivo_principal": "Facturación normal sin variación",
        "detalle_variacion": "Tu recibo mantiene la tarifa regular sin cobros adicionales.",
        "beneficios_actuales": "400 Mbps de fibra simétrica y acceso a la app Mi Movistar para gestión 24/7.",
        "antiguedad": "12 meses",
        "region": "Lima - Pueblo Libre",
        "lineas_moviles_activas": 1
    },
    "CLI004": {
        "id": "CLI004",
        "nombre": "Lucía Ramos",
        "servicio": "Plan Fibra 300 Mbps",
        "plan_actual": "Dúo Internet 300 Mbps + Fijo",
        "tipo_servicio": "HOGAR",
        "modalidad_facturacion": "Renta Adelantada",
        "tipo_producto_b2c": "Dúo Internet Fibra 300 Mbps + Fijo",
        "escenario_tag": "Escenario (a) Prorrateo Alta a Mitad de Ciclo",
        "telefono_movil": "976543210",
        "estado_linea_movil": "ACTIVA",
        "recibo_anterior": 69.90,
        "recibo_actual": 94.90,
        "diferencia": 25.00,
        "tipo_causa": "prorrateo",
        "motivo_principal": "Prorrateo por alta a mitad de ciclo",
        "detalle_variacion": "Cobro de días proporcionales por activación el día 12 del ciclo de facturación.",
        "beneficios_actuales": "300 Mbps estables en casa y llamadas ilimitadas a fijos nacionales.",
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
        "modalidad_facturacion": "Renta Vencida",
        "tipo_producto_b2c": "Móvil Postpago Ilimitado 65GB",
        "escenario_tag": "Escenario (b) Cuota de Equipo Financiado (ShEq)",
        "telefono_movil": "965432109",
        "estado_linea_movil": "ACTIVA",
        "recibo_anterior": 55.90,
        "recibo_actual": 90.90,
        "diferencia": 35.00,
        "tipo_causa": "cuota_equipo",
        "motivo_principal": "Cuota 3/12 de equipo financiado (Samsung Galaxy)",
        "detalle_variacion": "Cuota mensual por adquisición financiada de smartphone Samsung Galaxy.",
        "beneficios_actuales": "65GB de alta velocidad, minutos ilimitados y cobertura 4.5G a nivel nacional.",
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
        "modalidad_facturacion": "Renta Adelantada",
        "tipo_producto_b2c": "Dúo Básico 100 Mbps",
        "escenario_tag": "Escenario (c) Reconexión tras Suspensión Morosa",
        "telefono_movil": "954321098",
        "estado_linea_movil": "SUSPENDIDA_POR_PAGO",
        "recibo_anterior": 79.90,
        "recibo_actual": 90.40,
        "diferencia": 10.50,
        "tipo_causa": "reconexion_suspension",
        "motivo_principal": "Cargo por reconexión morosa (OC1_RECONEXION)",
        "detalle_variacion": "Cargo por rehabilitación tras suspensión temporal del servicio por pago fuera de fecha.",
        "beneficios_actuales": "Internet de 100 Mbps y telefonía fija para estar siempre comunicada en tu hogar.",
        "antiguedad": "9 meses",
        "region": "Chiclayo",
        "lineas_moviles_activas": 1
    },
    "CLI007": {
        "id": "CLI007",
        "nombre": "Pedro Gómez",
        "servicio": "Plan Fibra 200 Mbps",
        "plan_actual": "Plan Fibra 200 Mbps",
        "tipo_servicio": "HOGAR",
        "modalidad_facturacion": "Renta Adelantada",
        "tipo_producto_b2c": "Fibra Óptica 200 Mbps",
        "escenario_tag": "Compra de Paquete TV HD + Datos",
        "telefono_movil": "943210987",
        "estado_linea_movil": "ACTIVA",
        "recibo_anterior": 65.00,
        "recibo_actual": 85.00,
        "diferencia": 20.00,
        "tipo_causa": "compra_paquetes",
        "motivo_principal": "Compra de Paquete Bloque TV HD + 10GB",
        "detalle_variacion": "Adquisición de paquete complementario de contenido y datos solicitado en el ciclo.",
        "beneficios_actuales": "200 Mbps de fibra simétrica y acceso a los canales HD contratados en tu Smart TV.",
        "antiguedad": "11 meses",
        "region": "Cusco",
        "lineas_moviles_activas": 1
    },
    "CLI008": {
        "id": "CLI008",
        "nombre": "Elena Flores",
        "servicio": "Plan Fibra 500 Mbps",
        "plan_actual": "Plan Fibra 500 Mbps",
        "tipo_servicio": "HOGAR",
        "modalidad_facturacion": "Renta Adelantada",
        "tipo_producto_b2c": "Fibra Óptica 500 Mbps",
        "escenario_tag": "Nota de Crédito por Ajuste Técnico",
        "telefono_movil": "932109876",
        "estado_linea_movil": "ACTIVA",
        "recibo_anterior": 99.90,
        "recibo_actual": 79.90,
        "diferencia": -20.00,
        "tipo_causa": "nota_credito",
        "motivo_principal": "Nota de Crédito por Ajuste Técnico Facturado",
        "detalle_variacion": "Descuento contable de S/ 20.00 a favor por incidencia en velocidad de servicio.",
        "beneficios_actuales": "500 Mbps de alta velocidad con bono de fidelización activo en tu recibo.",
        "antiguedad": "16 meses",
        "region": "Piura",
        "lineas_moviles_activas": 1
    },
    "CLI009": {
        "id": "CLI009",
        "nombre": "David Morales",
        "servicio": "Plan Fibra 600 Mbps",
        "plan_actual": "Plan Fibra 600 Mbps Pro",
        "tipo_servicio": "HOGAR",
        "modalidad_facturacion": "Renta Adelantada",
        "tipo_producto_b2c": "Fibra Óptica 600 Mbps Pro",
        "escenario_tag": "Escenario (e) Cambio de Plan / Upgrade",
        "telefono_movil": "921098765",
        "estado_linea_movil": "ACTIVA",
        "recibo_anterior": 79.90,
        "recibo_actual": 109.90,
        "diferencia": 30.00,
        "tipo_causa": "cambio_plan",
        "motivo_principal": "Cambio de Plan a Fibra 1000 Mbps",
        "detalle_variacion": "Migración voluntaria de Plan Fibra 300 a Fibra 1000 con incremento de velocidad.",
        "beneficios_actuales": "1000 Mbps de fibra simétrica para navegación ultrarrápida en múltiples dispositivos.",
        "antiguedad": "20 meses",
        "region": "Huancayo",
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
        st.session_state.escalated_tickets = []

    if "selected_ticket_id" not in st.session_state:
        st.session_state.selected_ticket_id = None


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
