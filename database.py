"""
database.py - Módulo de Gestión de Base de Datos SQLite para Desafío 2 (Movistar)
Personalización Comercial Inteligente.
"""

import os
import sqlite3
from typing import Optional, Dict, Any, List

# Ruta por defecto de la base de datos SQLite
DEFAULT_DB_NAME = "movistar_desafio2.db"
DB_PATH = os.environ.get("MOVISTAR_DB_PATH", DEFAULT_DB_NAME)


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """
    Crea y retorna una conexión configurada a la base de datos SQLite.
    Habilita llaves foráneas (PRAGMA foreign_keys = ON) y modo WAL para alto rendimiento.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Optimización y consistencia de base de datos
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def create_schema(conn: sqlite3.Connection, drop_existing: bool = False) -> None:
    """
    Crea las tablas y los índices en la base de datos SQLite con tipado estricto.
    """
    cursor = conn.cursor()

    if drop_existing:
        cursor.execute("DROP TABLE IF EXISTS historial_campanias;")
        cursor.execute("DROP TABLE IF EXISTS clientes;")
        cursor.execute("DROP TABLE IF EXISTS catalogo_ofertas;")

    # 1. Tabla Catálogo de Ofertas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS catalogo_ofertas (
        oferta_id INTEGER PRIMARY KEY,
        nombre_oferta TEXT NOT NULL,
        tipo_oferta TEXT NOT NULL,
        cargo_fijo REAL NOT NULL,
        descuento_porcentaje REAL DEFAULT 0.0,
        precio_promocional REAL NOT NULL,
        velocidad_mbps INTEGER,
        gigas_datos INTEGER,
        descripcion TEXT,
        activo INTEGER DEFAULT 1 NOT NULL CHECK (activo IN (0, 1))
    );
    """)

    # 2. Tabla Clientes (con tipado estricto y manejo de nulos)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        cliente_id INTEGER PRIMARY KEY,
        monto_facturado_prom REAL NOT NULL,
        elegible_mt INTEGER NOT NULL CHECK (elegible_mt IN (0, 1)),
        es_movistar_total INTEGER NOT NULL CHECK (es_movistar_total IN (0, 1)),
        tipo_cliente TEXT,
        oferta_hogar_id INTEGER,
        antiguedad_meses INTEGER,
        lineas_moviles_activas INTEGER,
        score_propension_digital REAL,
        region TEXT,
        distrito TEXT,
        canal_preferido TEXT,
        FOREIGN KEY (oferta_hogar_id) REFERENCES catalogo_ofertas (oferta_id) ON DELETE SET NULL
    );
    """)

    # 3. Tabla Historial de Campañas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial_campanias (
        campania_id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        oferta_id INTEGER NOT NULL,
        fecha_contacto TEXT NOT NULL,
        canal_contacto TEXT NOT NULL,
        resultado TEXT NOT NULL,
        acepto_oferta INTEGER NOT NULL CHECK (acepto_oferta IN (0, 1)),
        FOREIGN KEY (cliente_id) REFERENCES clientes (cliente_id) ON DELETE CASCADE,
        FOREIGN KEY (oferta_id) REFERENCES catalogo_ofertas (oferta_id) ON DELETE CASCADE
    );
    """)

    # Creación de Índices para optimizar consultas de filtrado por cliente_id y oferta_id
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientes_cliente_id ON clientes (cliente_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientes_oferta_hogar_id ON clientes (oferta_hogar_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientes_elegible_mt ON clientes (elegible_mt);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientes_es_movistar_total ON clientes (es_movistar_total);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientes_tipo ON clientes (tipo_cliente);")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ofertas_oferta_id ON catalogo_ofertas (oferta_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ofertas_tipo ON catalogo_ofertas (tipo_oferta);")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_historial_cliente_id ON historial_campanias (cliente_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_historial_oferta_id ON historial_campanias (oferta_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_historial_cliente_oferta ON historial_campanias (cliente_id, oferta_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_historial_fecha ON historial_campanias (fecha_contacto);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_historial_acepto ON historial_campanias (acepto_oferta);")

    conn.commit()


def get_table_counts(conn: Optional[sqlite3.Connection] = None) -> Dict[str, int]:
    """Retorna el conteo actual de registros en cada tabla."""
    close_after = False
    if conn is None:
        conn = get_connection()
        close_after = True

    try:
        counts = {}
        for table in ["catalogo_ofertas", "clientes", "historial_campanias"]:
            cursor = conn.execute(f"SELECT COUNT(*) AS total FROM {table}")
            counts[table] = cursor.fetchone()["total"]
        return counts
    finally:
        if close_after:
            conn.close()


def get_cliente_by_id(cliente_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Obtiene el registro completo de un cliente por su ID."""
    close_after = False
    if conn is None:
        conn = get_connection()
        close_after = True

    try:
        cursor = conn.execute("""
            SELECT c.*, o.nombre_oferta AS nombre_oferta_hogar, o.precio_promocional AS precio_oferta_hogar
            FROM clientes c
            LEFT JOIN catalogo_ofertas o ON c.oferta_hogar_id = o.oferta_id
            WHERE c.cliente_id = ?
        """, (cliente_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        if close_after:
            conn.close()


def get_historial_por_cliente(cliente_id: int, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Retorna el historial completo de campañas contactadas a un cliente."""
    close_after = False
    if conn is None:
        conn = get_connection()
        close_after = True

    try:
        cursor = conn.execute("""
            SELECT h.*, o.nombre_oferta, o.tipo_oferta, o.precio_promocional
            FROM historial_campanias h
            JOIN catalogo_ofertas o ON h.oferta_id = o.oferta_id
            WHERE h.cliente_id = ?
            ORDER BY h.fecha_contacto DESC
        """, (cliente_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        if close_after:
            conn.close()


if __name__ == "__main__":
    conn = get_connection()
    create_schema(conn)
    counts = get_table_counts(conn)
    print("Schema creado exitosamente.")
    print("Conteos actuales:", counts)
    conn.close()
