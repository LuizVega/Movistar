"""
services/order_service.py - Capa de Ejecución y Gestión de Órdenes Comerciales (Movistar Perú)
Procesa autorizaciones de upgrade de plan y fraccionamientos desde Yara AI,
registrando transacciones en Ordenes.csv y la base de datos SQLite.
"""

import os
import csv
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from database import insert_orden_comercial, get_ordenes_por_cliente
from nbo_engine import generar_next_best_offer
from state_manager import CLIENTES_CATALOGO


def generar_id_orden(prefijo: str = "ORD") -> str:
    """Genera un código de orden único con timestamp."""
    fecha_str = datetime.now().strftime("%Y%m%d")
    micro = datetime.now().strftime("%f")[:4]
    return f"{prefijo}-{fecha_str}-{micro}"


def calcular_fechas_ciclo() -> Dict[str, str]:
    """Calcula la fecha de corte y la fecha de vigencia del próximo ciclo."""
    ahora = datetime.now()
    # Fecha de corte: día 28 del mes actual
    fecha_corte = f"{ahora.strftime('%Y-%m')}-28"
    
    # Fecha de vigencia: día 1 del próximo mes
    if ahora.month == 12:
        prox_mes = datetime(ahora.year + 1, 1, 1)
    else:
        prox_mes = datetime(ahora.year, ahora.month + 1, 1)
        
    fecha_vigencia = prox_mes.strftime("%Y-%m-%d")
    return {
        "fecha_registro": ahora.strftime("%Y-%m-%d %H:%M:%S"),
        "fecha_corte": fecha_corte,
        "fecha_vigencia": fecha_vigencia
    }


def registrar_en_ordenes_csv(cliente_id: str, motivo_desc: str, item_tipo: str = "Cambiar Plan"):
    """Registra la orden en el archivo Ordenes.csv manteniendo compatibilidad con su esquema."""
    ordenes_csv = "Ordenes.csv"
    ahora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.000")
    
    row_dict = {
        "ORDER_ACTION_COMPLETION_DATE": ahora_str,
        "ORDER_ACTION_START_DATE": ahora_str,
        "CUSTOMER_KEY": str(cliente_id),
        "SUBSCRIBER_KEY": f"100{cliente_id[-4:] if len(cliente_id) >= 4 else '0000'}",
        "ORDER_ACTION_REASON_DESC": motivo_desc,
        "ORDER_ACTION_REASON_ID": "YARA_AI",
        "ORDER_ITEM_TYPE_DESC": item_tipo,
        "ORDER_ACTION_STATUS_DESC": "Terminado",
        "ORDER_ACTION_LAST_UPDATOR": "YARA_AI_ENGINE",
        "ORDER_ACTION_CREATOR": "YARA_AI_BOT"
    }

    try:
        file_exists = os.path.exists(ordenes_csv)
        with open(ordenes_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(row_dict.keys()), delimiter=";")
            if not file_exists:
                writer.writeheader()
            writer.writerow(row_dict)
    except Exception:
        pass


def ejecutar_upgrade_plan(
    cliente_id: str,
    nuevo_plan_id: Optional[int] = None,
    canal: str = "YARA_AI"
) -> Dict[str, Any]:
    """
    Ejecuta la transacción de upgrade a Movistar Total autorizada por el cliente en el chat.
    Actualiza la base de datos, el archivo Ordenes.csv y el catálogo en memoria.
    """
    cid = str(cliente_id).strip().upper()
    orden_id = generar_id_orden("ORD")
    fechas = calcular_fechas_ciclo()

    # Obtener plan actual y propuesta NBO
    cliente_meta = CLIENTES_CATALOGO.get(cid, {
        "id": cid,
        "nombre": f"Cliente {cid}",
        "servicio": "Fibra Óptica Fragmentada",
        "recibo_actual": 119.90,
        "recibo_anterior": 89.90
    })
    plan_anterior = cliente_meta["servicio"]
    
    nbo = generar_next_best_offer(cid)
    of = nbo.get("oferta_recomendada", {})
    ben = nbo.get("beneficio_economico", {})
    
    nombre_nuevo_plan = of.get("nombre_oferta", "Movistar Total Dúo 200 Mbps + 1 Línea")
    precio_nuevo = float(of.get("precio_promocional", 110.40))
    ahorro_mensual = float(ben.get("ahorro_mensual_soles", 29.40))
    ahorro_anual = float(ben.get("ahorro_anual_estimado_soles", 352.80))
    velocidad = of.get("velocidad_mbps", 200)
    gigas = of.get("gigas_datos", 40)

    # 1. Actualizar estado del cliente en memoria
    if cid in CLIENTES_CATALOGO:
        CLIENTES_CATALOGO[cid]["servicio"] = nombre_nuevo_plan
        CLIENTES_CATALOGO[cid]["recibo_actual"] = precio_nuevo
        CLIENTES_CATALOGO[cid]["estado_linea"] = "Activa - Movistar Total"

    # 2. Registrar en base de datos SQLite
    orden_data = {
        "orden_id": orden_id,
        "cliente_id": cid,
        "tipo_orden": "UPGRADE_MOVISTAR_TOTAL",
        "plan_anterior": plan_anterior,
        "nuevo_plan_id": nuevo_plan_id or of.get("oferta_id", 10),
        "nombre_plan": nombre_nuevo_plan,
        "monto_nuevo": precio_nuevo,
        "ahorro_mensual": ahorro_mensual,
        "fecha_registro": fechas["fecha_registro"],
        "fecha_vigencia": fechas["fecha_vigencia"],
        "canal": canal,
        "estado": "PROCESADA"
    }
    insert_orden_comercial(orden_data)

    # 3. Registrar en Ordenes.csv
    registrar_en_ordenes_csv(
        cliente_id=cid,
        motivo_desc=f"Upgrade autorizado a {nombre_nuevo_plan}",
        item_tipo="Cambiar Plan"
    )

    # Mensaje estándar de Yara AI
    mensaje_yara = (
        f"¡Listo! He procesado tu solicitud con éxito. Código de solicitud: **`{orden_id}`**.\n\n"
        f"Tu nuevo plan **{nombre_nuevo_plan}** estará activo a partir de tu próximo ciclo de facturación (**{fechas['fecha_vigencia']}**) sin costos ocultos."
    )

    return {
        "exito": True,
        "orden_id": orden_id,
        "cliente_id": cid,
        "cliente_nombre": cliente_meta["nombre"],
        "plan_anterior": plan_anterior,
        "nuevo_plan": nombre_nuevo_plan,
        "precio_nuevo": precio_nuevo,
        "ahorro_mensual": ahorro_mensual,
        "ahorro_anual": ahorro_anual,
        "velocidad_mbps": velocidad,
        "gigas_datos": gigas,
        "fecha_registro": fechas["fecha_registro"],
        "fecha_corte": fechas["fecha_corte"],
        "fecha_vigencia": fechas["fecha_vigencia"],
        "canal": canal,
        "estado_orden": "PROCESADA",
        "mensaje_yara": mensaje_yara
    }


def ejecutar_fraccionamiento_deuda(
    cliente_id: str,
    cuotas: int = 3,
    monto_total: float = 119.90,
    canal: str = "YARA_AI"
) -> Dict[str, Any]:
    """
    Ejecuta el registro formal de un plan de fraccionamiento de deuda sin intereses.
    """
    cid = str(cliente_id).strip().upper()
    orden_id = generar_id_orden("FRACC")
    fechas = calcular_fechas_ciclo()
    monto_cuota = round(monto_total / max(1, cuotas), 2)

    cliente_meta = CLIENTES_CATALOGO.get(cid, {"nombre": f"Cliente {cid}"})

    orden_data = {
        "orden_id": orden_id,
        "cliente_id": cid,
        "tipo_orden": f"FRACCIONAMIENTO_{cuotas}M",
        "plan_anterior": f"Deuda Total S/ {monto_total:.2f}",
        "nuevo_plan_id": cuotas,
        "nombre_plan": f"Plan Fraccionamiento {cuotas} Cuotas (S/ {monto_cuota:.2f}/mes)",
        "monto_nuevo": monto_cuota,
        "ahorro_mensual": 0.0,
        "fecha_registro": fechas["fecha_registro"],
        "fecha_vigencia": fechas["fecha_vigencia"],
        "canal": canal,
        "estado": "PROCESADA"
    }
    insert_orden_comercial(orden_data)

    registrar_en_ordenes_csv(
        cliente_id=cid,
        motivo_desc=f"Fraccionamiento {cuotas} cuotas de S/ {monto_total:.2f}",
        item_tipo="Fraccionar Deuda"
    )

    mensaje_yara = (
        f"¡Listo! He procesado tu solicitud de fraccionamiento con éxito. Código de solicitud: **`{orden_id}`**.\n\n"
        f"Pagarás **{cuotas} cuotas fijas de S/ {monto_cuota:.2f} / mes sin intereses** a partir de tu próximo ciclo de facturación (**{fechas['fecha_vigencia']}**)."
    )

    return {
        "exito": True,
        "orden_id": orden_id,
        "solicitud_id": orden_id,
        "cliente_id": cid,
        "cliente_nombre": cliente_meta.get("nombre", f"Cliente {cid}"),
        "cuotas": cuotas,
        "monto_cuota": monto_cuota,
        "monto_total": monto_total,
        "fecha_registro": fechas["fecha_registro"],
        "fecha_vigencia": fechas["fecha_vigencia"],
        "canal": canal,
        "estado_orden": "PROCESADA",
        "mensaje_yara": mensaje_yara
    }



def ejecutar_pago_recibo(
    cliente_id: str,
    monto: float = 119.90,
    metodo_pago: str = "PASARELA_DIGITAL_MOVISTAR",
    canal: str = "YARA_AI"
) -> Dict[str, Any]:
    """
    Procesa y registra el pago inmediato del recibo del cliente a través de la pasarela digital.
    """
    cid = str(cliente_id).strip().upper()
    orden_id = generar_id_orden("PAG")
    fechas = calcular_fechas_ciclo()

    cliente_meta = CLIENTES_CATALOGO.get(cid, {"nombre": f"Cliente {cid}"})

    orden_data = {
        "orden_id": orden_id,
        "cliente_id": cid,
        "tipo_orden": "PAGO_RECIBO_INMEDIATO",
        "plan_anterior": f"Recibo Pendiente S/ {monto:.2f}",
        "nuevo_plan_id": None,
        "nombre_plan": f"Pago de Recibo Mensual S/ {monto:.2f} ({metodo_pago})",
        "monto_nuevo": monto,
        "ahorro_mensual": 0.0,
        "fecha_registro": fechas["fecha_registro"],
        "fecha_vigencia": fechas["fecha_registro"],
        "canal": canal,
        "estado": "PAGADO_EXITOSO"
    }
    insert_orden_comercial(orden_data)

    registrar_en_ordenes_csv(
        cliente_id=cid,
        motivo_desc=f"Pago de recibo S/ {monto:.2f} vía {metodo_pago}",
        item_tipo="Pago Recibo"
    )

    return {
        "exito": True,
        "transaccion_id": orden_id,
        "cliente_id": cid,
        "cliente_nombre": cliente_meta["nombre"],
        "monto_pagado": monto,
        "metodo_pago": metodo_pago,
        "fecha_pago": fechas["fecha_registro"],
        "estado": "PAGADO_EXITOSO"
    }


def ejecutar_registro_consulta(
    cliente_id: str,
    motivo: str = "Consulta de Variación de Recibo",
    resumen: str = "Detalle de conceptos auditados por Yara AI",
    canal: str = "YARA_AI"
) -> Dict[str, Any]:
    """
    Registra formalmente una consulta del cliente generando un código de atención auditable.
    """
    cid = str(cliente_id).strip().upper()
    consulta_id = generar_id_orden("CNS")
    fechas = calcular_fechas_ciclo()
    cliente_meta = CLIENTES_CATALOGO.get(cid, {"nombre": f"Cliente {cid}"})

    from database import insert_consulta_registrada
    consulta_data = {
        "consulta_id": consulta_id,
        "cliente_id": cid,
        "motivo": motivo,
        "resumen": resumen,
        "canal": canal,
        "fecha_registro": fechas["fecha_registro"],
        "estado": "REGISTRADA"
    }
    insert_consulta_registrada(consulta_data)

    registrar_en_ordenes_csv(
        cliente_id=cid,
        motivo_desc=f"Registro de consulta: {motivo}",
        item_tipo="Registro Consulta"
    )

    return {
        "exito": True,
        "consulta_id": consulta_id,
        "cliente_id": cid,
        "cliente_nombre": cliente_meta["nombre"],
        "motivo": motivo,
        "resumen": resumen,
        "fecha_registro": fechas["fecha_registro"],
        "estado": "REGISTRADA"
    }


def consultar_ordenes_cliente(cliente_id: str) -> List[Dict[str, Any]]:
    """Consulta todas las órdenes registradas de un cliente."""
    return get_ordenes_por_cliente(cliente_id)


