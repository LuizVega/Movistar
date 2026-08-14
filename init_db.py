"""
init_db.py - Script de Inicialización y Carga de Datos para Desafío 2 (Movistar)
Personalización Comercial Inteligente.

Este script:
1. Crea/reinicializa las tablas e índices en SQLite.
2. Parsea y carga los 3 datasets CSV:
   - catalogo_ofertas_entrega.csv (22 ofertas)
   - dataset_clientes.csv (100,000 clientes sintéticos)
   - historial_campanias.csv (historial de campañas)
3. Aplica tipado estricto (FLOAT, BOOLEAN) y manejo robusto de valores nulos (NULL).
4. Si los datasets sintéticos no existen previamente en el disco, los genera automáticamente
   según la especificación del Desafío 2 y los carga.
5. Imprime en consola los conteos de confirmación exactos.
"""

import os
import csv
import random
import sqlite3
from typing import Optional, Any, List, Dict, Tuple
from database import get_connection, create_schema, get_table_counts, DB_PATH

# Nombres de archivos CSV objetivo
CSV_OFERTAS = "catalogo_ofertas_entrega.csv"
CSV_CLIENTES = "dataset_clientes.csv"
CSV_CAMPANIAS = "historial_campanias.csv"


# ==========================================
# Funciones de parseo y limpieza estricta
# ==========================================

def parse_nullable_str(val: Any) -> Optional[str]:
    """Limpia cadenas de texto y convierte valores vacíos o nulos en None (SQL NULL)."""
    if val is None:
        return None
    val_str = str(val).strip()
    if val_str.lower() in ("", "null", "none", "nan", "undefined", "-", "n/a"):
        return None
    return val_str


def parse_float(val: Any, default: float = 0.0) -> float:
    """Convierte de forma segura a FLOAT, manejando formatos monetarios o comas decimales."""
    if val is None:
        return default
    val_str = str(val).strip().replace("S/", "").replace("$", "").replace(",", ".")
    if not val_str or val_str.lower() in ("null", "none", "nan", "-"):
        return default
    try:
        return float(val_str)
    except (ValueError, TypeError):
        return default


def parse_bool(val: Any, default: int = 0) -> int:
    """
    Convierte de forma estricta valores a BOOLEAN (representado como 0 o 1 en SQLite).
    Soporta True/False, 'true'/'false', 1/0, 'si'/'no', 's'/'n', 't'/'f'.
    """
    if val is None:
        return default
    val_str = str(val).strip().lower()
    if val_str in ("1", "true", "t", "si", "sí", "s", "yes", "y"):
        return 1
    if val_str in ("0", "false", "f", "no", "n"):
        return 0
    return default


def parse_nullable_int(val: Any) -> Optional[int]:
    """Convierte a entero o retorna None si el valor es nulo o vacío."""
    if val is None:
        return None
    val_str = str(val).strip()
    if val_str.lower() in ("", "null", "none", "nan", "undefined", "-"):
        return None
    try:
        return int(float(val_str))
    except (ValueError, TypeError):
        return None


# =========================================================
# Generador de Datasets Sintéticos (Desafío 2 - 100,000 Clientes)
# =========================================================

def generate_synthetic_data_if_missing():
    """
    Genera los 3 archivos CSV sintéticos requeridos para el Desafío 2 si no están presentes:
    - 22 ofertas del catálogo comercial de Movistar.
    - 100,000 clientes sintéticos con distribución realista y valores nulos controlados.
    - Historial de campañas de contacto.
    """
    # 1. Catálogo de ofertas (22 filas)
    if not os.path.exists(CSV_OFERTAS):
        print(f"[INFO] Generando dataset sintético: {CSV_OFERTAS} (22 ofertas)...")
        ofertas = [
            (1, "Fibra Óptica 100 Mbps", "FIBRA", 69.90, 0.0, 69.90, 100, None, "Internet simétrico para hogar 100 Mbps", 1),
            (2, "Fibra Óptica 200 Mbps Promo", "FIBRA", 89.90, 15.0, 76.40, 200, None, "Internet simétrico 200 Mbps con 15% de descuento", 1),
            (3, "Fibra Óptica 300 Mbps Gamer", "FIBRA", 109.90, 10.0, 98.90, 300, None, "Baja latencia y ultra velocidad simétrica", 1),
            (4, "Fibra Óptica 500 Mbps Pro", "FIBRA", 139.90, 20.0, 111.90, 500, None, "Alta velocidad para hogares multi-dispositivo", 1),
            (5, "Fibra Óptica 1000 Mbps Giga", "FIBRA", 199.90, 25.0, 149.90, 1000, None, "Máxima velocidad para streaming 4K y gaming extremo", 1),
            (6, "Móvil Ilimitado Básico 40GB", "MOVIL", 39.90, 0.0, 39.90, None, 40, "Minutos y SMS ilimitados + 40GB en alta velocidad", 1),
            (7, "Móvil Ilimitado Plus 65GB", "MOVIL", 55.90, 10.0, 50.30, None, 65, "Minutos ilimitados + 65GB + Roaming internacional", 1),
            (8, "Móvil Ilimitado Total 100GB", "MOVIL", 69.90, 15.0, 59.40, None, 100, "Minutos ilimitados + 100GB + Apps ilimitadas", 1),
            (9, "Móvil Ilimitado Ultra 5G", "MOVIL", 89.90, 20.0, 71.90, None, 999, "Gigas ilimitados en red 5G con tethering full", 1),
            (10, "Movistar Total Dúo 200 Mbps + 1 Línea", "MOVISTAR_TOTAL", 129.90, 15.0, 110.40, 200, 65, "Fibra 200 Mbps + Móvil 65GB en un solo recibo", 1),
            (11, "Movistar Total Dúo 300 Mbps + 2 Líneas", "MOVISTAR_TOTAL", 169.90, 20.0, 135.90, 300, 100, "Fibra 300 Mbps + 2 Líneas móviles compartidas", 1),
            (12, "Movistar Total Dúo 500 Mbps + 3 Líneas", "MOVISTAR_TOTAL", 219.90, 25.0, 164.90, 500, 150, "Fibra 500 Mbps + 3 Líneas ilimitadas", 1),
            (13, "Movistar Total Trío 300 Mbps + TV + Móvil", "MOVISTAR_TOTAL", 199.90, 15.0, 169.90, 300, 65, "Fibra 300 Mbps + Movistar TV Estándar + 1 Línea Móvil", 1),
            (14, "Movistar Total Trío 500 Mbps + TV HD + 2 Líneas", "MOVISTAR_TOTAL", 259.90, 20.0, 207.90, 500, 100, "Fibra 500 Mbps + Movistar TV HD + 2 Líneas Móviles", 1),
            (15, "Movistar Total Trío 1000 Mbps + TV Estelar + 3 Líneas", "MOVISTAR_TOTAL", 349.90, 25.0, 262.40, 1000, 200, "Fibra 1Gbps + TV Estelar Premium + 3 Líneas Full", 1),
            (16, "Dúo Fibra 100 Mbps + Fijo Ilimitado", "DUO", 79.90, 0.0, 79.90, 100, None, "Internet simétrico 100 Mbps + telefonía fija local ilimitada", 1),
            (17, "Dúo Fibra 300 Mbps + Movistar TV App", "DUO", 119.90, 10.0, 107.90, 300, None, "Internet simétrico 300 Mbps + acceso a Movistar TV App", 1),
            (18, "Trío Fibra 200 Mbps + TV Estándar + Fijo", "TRIO", 149.90, 15.0, 127.40, 200, None, "Internet 200 Mbps + Decodificador HD + Telefonía fija", 1),
            (19, "Trío Fibra 500 Mbps + TV HD Premium + Fijo", "TRIO", 219.90, 20.0, 175.90, 500, None, "Internet 500 Mbps + Pack Canales Premium + Fijo ilimitado", 1),
            (20, "Plan Pyme Fibra Pro 300 Mbps con IP Fija", "PYME", 169.90, 10.0, 152.90, 300, None, "Internet garantizado 1:1 con IP pública fija y soporte 24/7", 1),
            (21, "Plan Pyme Trío 500 Mbps + 2 Líneas Fijas", "PYME", 279.90, 15.0, 237.90, 500, None, "Solución integral para negocios: internet, TV corporativa y telefonía", 1),
            (22, "Upgrade Velocidad +100 Mbps Adicional", "UPGRADE", 19.90, 0.0, 19.90, 100, None, "Aumento de velocidad para clientes existentes de Fibra", 1),
        ]
        with open(CSV_OFERTAS, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["oferta_id", "nombre_oferta", "tipo_oferta", "cargo_fijo", "descuento_porcentaje", "precio_promocional", "velocidad_mbps", "gigas_datos", "descripcion", "activo"])
            writer.writerows(ofertas)

    # 2. Clientes sintéticos (100,000 filas)
    if not os.path.exists(CSV_CLIENTES):
        print(f"[INFO] Generando dataset sintético: {CSV_CLIENTES} (100,000 clientes)...")
        random.seed(42)  # Semilla para reproducibilidad estricta
        regiones = ["LIMA", "AREQUIPA", "LA LIBERTAD", "PIURA", "CUSCO", "LAMBAYEQUE", "JUNIN", "ANCASH", "CALLAO", "ICA"]
        distritos_lima = ["MIRAFLORES", "SAN ISIDRO", "SURCO", "SAN BORJA", "LIMA CENTRO", "LOS OLIVOS", "SAN MIGUEL", "MAGDALENA", "JESUS MARIA", "CHORRILLOS", "SURQUILLO", "LA MOLINA"]
        tipos_cliente = ["RESIDENCIAL", "RESIDENCIAL", "RESIDENCIAL", "RESIDENCIAL", "PYME", "CORPORATIVO", None]
        canales = ["APP_MOVISTAR", "WHATSAPP", "CALL_CENTER", "SMS", "EMAIL", "TIENDA_FISICA"]

        with open(CSV_CLIENTES, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "cliente_id", "monto_facturado_prom", "elegible_mt", "es_movistar_total",
                "tipo_cliente", "oferta_hogar_id", "antiguedad_meses", "lineas_moviles_activas",
                "score_propension_digital", "region", "distrito", "canal_preferido"
            ])

            for cid in range(1000001, 1000001 + 100000):
                # Generación controlada de variables según reglas de negocio
                es_mt = 1 if random.random() < 0.18 else 0
                elegible_mt = 0 if es_mt == 1 else (1 if random.random() < 0.45 else 0)
                
                # Monto facturado promedio (FLOAT)
                if es_mt:
                    monto = round(random.uniform(130.0, 320.0), 2)
                else:
                    monto = round(random.uniform(35.0, 180.0), 2)

                # Tipo de cliente con valores nulos ocasionales para validación
                tipo_c = random.choice(tipos_cliente)
                
                # Oferta hogar actual (NULL para clientes solo móvil o sin hogar)
                if random.random() < 0.70:
                    oferta_hogar = random.randint(1, 22)
                else:
                    oferta_hogar = None

                antiguedad = random.randint(1, 120)
                lineas_moviles = random.randint(1, 5) if (es_mt or random.random() < 0.6) else 0
                score_prop = round(random.uniform(0.05, 0.99), 4)
                region = random.choice(regiones)
                distrito = random.choice(distritos_lima) if region in ("LIMA", "CALLAO") else f"CAPITAL_{region}"
                canal = random.choice(canales)

                writer.writerow([
                    cid,
                    monto,
                    elegible_mt,
                    es_mt,
                    tipo_c if tipo_c is not None else "",
                    oferta_hogar if oferta_hogar is not None else "",
                    antiguedad,
                    lineas_moviles,
                    score_prop,
                    region,
                    distrito,
                    canal
                ])

    # 3. Historial de campañas sintético (150,000 interacciones)
    if not os.path.exists(CSV_CAMPANIAS):
        print(f"[INFO] Generando dataset sintético: {CSV_CAMPANIAS} (150,000 registros)...")
        random.seed(42)
        canales_contacto = ["CALL_CENTER", "APP_MOVISTAR", "WHATSAPP", "SMS", "EMAIL"]
        resultados = ["ACEPTADA", "RECHAZADA", "NO_CONTACTADO", "PENDIENTE"]

        with open(CSV_CAMPANIAS, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["campania_id", "cliente_id", "oferta_id", "fecha_contacto", "canal_contacto", "resultado", "acepto_oferta"])

            for camp_id in range(1, 150001):
                cliente_id = random.randint(1000001, 1000001 + 99999)
                oferta_id = random.randint(1, 22)
                
                # Fechas recientes (2025 - 2026)
                mes = random.randint(1, 12)
                dia = random.randint(1, 28)
                anio = random.choice([2025, 2026])
                fecha_contacto = f"{anio:04d}-{mes:02d}-{dia:02d}"

                canal = random.choice(canales_contacto)
                res = random.choices(resultados, weights=[0.22, 0.48, 0.20, 0.10])[0]
                acepto = 1 if res == "ACEPTADA" else 0

                writer.writerow([camp_id, cliente_id, oferta_id, fecha_contacto, canal, res, acepto])


# =========================================================
# Funciones de Carga Masiva a SQLite con Tipado Estricto
# =========================================================

def load_catalogo_ofertas(conn: sqlite3.Connection, csv_path: str = CSV_OFERTAS) -> int:
    """
    Parsea y carga catalogo_ofertas_entrega.csv en la tabla catalogo_ofertas.
    """
    if not os.path.exists(csv_path):
        # Fallback a CATALOGO-OFERTAS.csv si existe
        if os.path.exists("CATALOGO-OFERTAS.csv"):
            csv_path = "CATALOGO-OFERTAS.csv"
        else:
            raise FileNotFoundError(f"No se encontró el archivo de catálogo: {csv_path}")

    # Detección de delimitador
    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
        first_line = f.readline()
        delimiter = ";" if ";" in first_line and first_line.count(";") > first_line.count(",") else ","

    rows_to_insert = []
    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for idx, row in enumerate(reader, start=1):
            # Normalización de claves (minúsculas y sin espacios)
            r = {k.strip().lower().replace(" ", "_"): v for k, v in row.items() if k}
            
            oferta_id = parse_nullable_int(r.get("oferta_id") or r.get("id") or idx)
            nombre = parse_nullable_str(r.get("nombre_oferta") or r.get("charge_code_desc") or r.get("charge_code") or f"Oferta {oferta_id}")
            tipo = parse_nullable_str(r.get("tipo_oferta") or r.get("tipo_de_renta") or "GENERAL") or "GENERAL"
            cargo_fijo = parse_float(r.get("cargo_fijo") or r.get("rate_final") or r.get("precio"))
            descuento = parse_float(r.get("descuento_porcentaje") or r.get("descuento"), default=0.0)
            precio_promo = parse_float(r.get("precio_promocional") or r.get("rate_final") or (cargo_fijo * (1 - descuento / 100.0)))
            velocidad = parse_nullable_int(r.get("velocidad_mbps") or r.get("velocidad"))
            gigas = parse_nullable_int(r.get("gigas_datos") or r.get("gigas"))
            descripcion = parse_nullable_str(r.get("descripcion"))
            activo = parse_bool(r.get("activo", 1), default=1)

            rows_to_insert.append((
                oferta_id, nombre, tipo, cargo_fijo, descuento, precio_promo, velocidad, gigas, descripcion, activo
            ))

    cursor = conn.cursor()
    cursor.executemany("""
        INSERT OR REPLACE INTO catalogo_ofertas (
            oferta_id, nombre_oferta, tipo_oferta, cargo_fijo, descuento_porcentaje,
            precio_promocional, velocidad_mbps, gigas_datos, descripcion, activo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, rows_to_insert)
    conn.commit()

    return len(rows_to_insert)


def load_clientes(conn: sqlite3.Connection, csv_path: str = CSV_CLIENTES, batch_size: int = 10000) -> int:
    """
    Parsea y carga dataset_clientes.csv en la tabla clientes con tipado estricto:
    - monto_facturado_prom como FLOAT
    - elegible_mt y es_movistar_total como BOOLEAN (0/1)
    - Manejo de NULL en tipo_cliente y oferta_hogar_id.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"No se encontró el archivo de clientes: {csv_path}")

    # Detección de delimitador
    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
        first_line = f.readline()
        delimiter = ";" if ";" in first_line and first_line.count(";") > first_line.count(",") else ","

    cursor = conn.cursor()
    total_loaded = 0
    batch = []

    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for idx, row in enumerate(reader, start=1):
            r = {k.strip().lower().replace(" ", "_"): v for k, v in row.items() if k}

            cliente_id = parse_nullable_int(r.get("cliente_id") or r.get("cod_cliente") or r.get("customer_key") or idx)
            monto_facturado = parse_float(r.get("monto_facturado_prom") or r.get("monto_facturado") or r.get("arpu") or r.get("charge_total_amount"))
            elegible_mt = parse_bool(r.get("elegible_mt"))
            es_mt = parse_bool(r.get("es_movistar_total") or r.get("es_mt"))
            
            # Manejo estricto de nulos para campos categóricos y llaves foráneas
            tipo_cliente = parse_nullable_str(r.get("tipo_cliente") or r.get("lob_type"))
            oferta_hogar_id = parse_nullable_int(r.get("oferta_hogar_id"))
            
            antiguedad = parse_nullable_int(r.get("antiguedad_meses") or r.get("antiguedad"))
            lineas_moviles = parse_nullable_int(r.get("lineas_moviles_activas") or r.get("lineas_moviles"))
            score_propension = parse_float(r.get("score_propension_digital") or r.get("score_propension"), default=None) if (r.get("score_propension_digital") or r.get("score_propension")) else None
            region = parse_nullable_str(r.get("region"))
            distrito = parse_nullable_str(r.get("distrito"))
            canal_preferido = parse_nullable_str(r.get("canal_preferido"))

            batch.append((
                cliente_id, monto_facturado, elegible_mt, es_mt, tipo_cliente,
                oferta_hogar_id, antiguedad, lineas_moviles, score_propension,
                region, distrito, canal_preferido
            ))

            if len(batch) >= batch_size:
                cursor.executemany("""
                    INSERT OR REPLACE INTO clientes (
                        cliente_id, monto_facturado_prom, elegible_mt, es_movistar_total,
                        tipo_cliente, oferta_hogar_id, antiguedad_meses, lineas_moviles_activas,
                        score_propension_digital, region, distrito, canal_preferido
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, batch)
                conn.commit()
                total_loaded += len(batch)
                batch = []

    if batch:
        cursor.executemany("""
            INSERT OR REPLACE INTO clientes (
                cliente_id, monto_facturado_prom, elegible_mt, es_movistar_total,
                tipo_cliente, oferta_hogar_id, antiguedad_meses, lineas_moviles_activas,
                score_propension_digital, region, distrito, canal_preferido
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, batch)
        conn.commit()
        total_loaded += len(batch)

    return total_loaded


def load_historial_campanias(conn: sqlite3.Connection, csv_path: str = CSV_CAMPANIAS, batch_size: int = 10000) -> int:
    """
    Parsea y carga historial_campanias.csv en la tabla historial_campanias.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"No se encontró el archivo de historial: {csv_path}")

    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
        first_line = f.readline()
        delimiter = ";" if ";" in first_line and first_line.count(";") > first_line.count(",") else ","

    cursor = conn.cursor()
    total_loaded = 0
    batch = []

    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for idx, row in enumerate(reader, start=1):
            r = {k.strip().lower().replace(" ", "_"): v for k, v in row.items() if k}

            campania_id = parse_nullable_int(r.get("campania_id") or r.get("id") or idx)
            cliente_id = parse_nullable_int(r.get("cliente_id") or r.get("cod_cliente"))
            oferta_id = parse_nullable_int(r.get("oferta_id"))
            fecha_contacto = parse_nullable_str(r.get("fecha_contacto") or r.get("fecha") or "2026-01-01")
            canal_contacto = parse_nullable_str(r.get("canal_contacto") or r.get("canal") or "CALL_CENTER")
            resultado = parse_nullable_str(r.get("resultado") or r.get("estado") or "PENDIENTE")
            acepto_oferta = parse_bool(r.get("acepto_oferta") or (1 if resultado == "ACEPTADA" else 0))

            if cliente_id and oferta_id:
                batch.append((
                    campania_id, cliente_id, oferta_id, fecha_contacto,
                    canal_contacto, resultado, acepto_oferta
                ))

            if len(batch) >= batch_size:
                cursor.executemany("""
                    INSERT OR REPLACE INTO historial_campanias (
                        campania_id, cliente_id, oferta_id, fecha_contacto,
                        canal_contacto, resultado, acepto_oferta
                    ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """, batch)
                conn.commit()
                total_loaded += len(batch)
                batch = []

    if batch:
        cursor.executemany("""
            INSERT OR REPLACE INTO historial_campanias (
                campania_id, cliente_id, oferta_id, fecha_contacto,
                canal_contacto, resultado, acepto_oferta
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """, batch)
        conn.commit()
        total_loaded += len(batch)

    return total_loaded


# ==========================================
# Ejecución Principal
# ==========================================

def init_database(db_path: str = DB_PATH, reset_db: bool = True):
    """Inicializa la base de datos, crea el esquema e inserta los datos."""
    # 1. Asegurar la presencia de datos sintéticos si no existen
    generate_synthetic_data_if_missing()

    # 2. Conectar y crear esquema
    conn = get_connection(db_path)
    create_schema(conn, drop_existing=reset_db)

    # 3. Cargar catálogo de ofertas
    n_ofertas = load_catalogo_ofertas(conn, CSV_OFERTAS)
    print(f"Catálogo de ofertas cargado: {n_ofertas:,} filas")

    # 4. Cargar dataset de clientes
    n_clientes = load_clientes(conn, CSV_CLIENTES)
    print(f"Clientes cargados: {n_clientes:,} filas")

    # 5. Cargar historial de campañas
    n_campanias = load_historial_campanias(conn, CSV_CAMPANIAS)
    print(f"Historial de campañas cargado: {n_campanias:,} filas")

    # 6. Validar integridad de datos con consulta directa
    counts = get_table_counts(conn)
    conn.close()

    return counts


if __name__ == "__main__":
    init_database()
