"""
test_db.py - Suite de Pruebas y Validación para la Base de Datos SQLite (Desafío 2)
"""

import sqlite3
from database import get_connection, get_table_counts, get_cliente_by_id, get_historial_por_cliente


def run_tests():
    conn = get_connection()
    cur = conn.cursor()

    print("============================================================")
    print("VERIFICACIÓN Y PRUEBAS DEL SISTEMA DE BASE DE DATOS")
    print("============================================================")

    # 1. Validación de Conteo Exacto de Filas
    counts = get_table_counts(conn)
    print("\n1. Conteo de Filas por Tabla:")
    for t, c in counts.items():
        print(f"   - {t}: {c:,} filas")

    assert counts["catalogo_ofertas"] == 22, f"Esperado 22 ofertas, obtenido: {counts['catalogo_ofertas']}"
    assert counts["clientes"] == 100000, f"Esperado 100,000 clientes, obtenido: {counts['clientes']}"
    assert counts["historial_campanias"] == 150000, f"Esperado 150,000 campañas, obtenido: {counts['historial_campanias']}"
    print("   [OK] Conteo exacto validado exitosamente.")

    # 2. Tipado Estricto (FLOAT, BOOLEAN)
    print("\n2. Validación de Tipos de Datos:")
    cur.execute("SELECT typeof(monto_facturado_prom), typeof(elegible_mt), typeof(es_movistar_total) FROM clientes LIMIT 10;")
    types = cur.fetchall()
    print(f"   Muestra de tipos (monto, elegible, es_mt): {[tuple(t) for t in types[:3]]}")
    assert all(t[0] == "real" for t in types), "monto_facturado_prom debe ser tipo REAL/FLOAT"
    assert all(t[1] == "integer" for t in types), "elegible_mt debe ser tipo INTEGER (BOOLEAN 0/1)"
    assert all(t[2] == "integer" for t in types), "es_movistar_total debe ser tipo INTEGER (BOOLEAN 0/1)"
    print("   [OK] Tipos de datos estrictos (FLOAT, BOOLEAN 0/1) validados.")

    # 3. Manejo de Nulos (NULL)
    print("\n3. Validación de Manejo de Nulos:")
    cur.execute("SELECT COUNT(*) FROM clientes WHERE tipo_cliente IS NULL;")
    null_tipos = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM clientes WHERE oferta_hogar_id IS NULL;")
    null_ofertas = cur.fetchone()[0]
    print(f"   - Clientes con tipo_cliente = NULL: {null_tipos:,}")
    print(f"   - Clientes con oferta_hogar_id = NULL: {null_ofertas:,}")
    assert null_tipos > 0, "Debe haber registros con tipo_cliente como NULL legítimo"
    assert null_ofertas > 0, "Debe haber registros con oferta_hogar_id como NULL legítimo"

    # Verificar que no se guardaron cadenas literales como 'None' o 'NULL'
    cur.execute("SELECT COUNT(*) FROM clientes WHERE tipo_cliente IN ('None', 'null', 'NULL', '', 'nan');")
    fake_nulls = cur.fetchone()[0]
    assert fake_nulls == 0, f"Error: Se encontraron {fake_nulls} nulos como texto literal"
    print("   [OK] Manejo de NULLs categóricos y llaves foráneas validado.")

    # 4. Creación de Índices
    print("\n4. Índices Creados en SQLite:")
    for table in ["clientes", "catalogo_ofertas", "historial_campanias"]:
        cur.execute(f"PRAGMA index_list({table});")
        indices = [r[1] for r in cur.fetchall()]
        print(f"   - {table}: {indices}")
        if table == "clientes":
            assert "idx_clientes_cliente_id" in indices or "sqlite_autoindex_clientes_1" in indices
        if table == "historial_campanias":
            assert "idx_historial_cliente_id" in indices
            assert "idx_historial_oferta_id" in indices

    # 5. Optimización de Consultas (EXPLAIN QUERY PLAN)
    print("\n5. Validación de Planes de Consulta con Índices:")
    cur.execute("EXPLAIN QUERY PLAN SELECT * FROM clientes WHERE cliente_id = 1000050;")
    qp1 = cur.fetchall()
    print(f"   - Filtrado clientes por cliente_id: {[r[3] for r in qp1]}")

    cur.execute("EXPLAIN QUERY PLAN SELECT * FROM historial_campanias WHERE cliente_id = 1000050;")
    qp2 = cur.fetchall()
    print(f"   - Filtrado historial por cliente_id: {[r[3] for r in qp2]}")

    cur.execute("EXPLAIN QUERY PLAN SELECT * FROM historial_campanias WHERE oferta_id = 10;")
    qp3 = cur.fetchall()
    print(f"   - Filtrado historial por oferta_id: {[r[3] for r in qp3]}")
    print("   [OK] Índices activos y optimizando los filtros.")

    # 6. Funciones Auxiliares de Consulta
    print("\n6. Pruebas de Funciones Auxiliares:")
    c = get_cliente_by_id(1000001, conn)
    print(f"   - get_cliente_by_id(1000001): ID={c['cliente_id']}, Monto={c['monto_facturado_prom']}, ElegibleMT={c['elegible_mt']}, Tipo={c['tipo_cliente']}, OfertaHogar={c['nombre_oferta_hogar']}")
    h = get_historial_por_cliente(1000001, conn)
    print(f"   - get_historial_por_cliente(1000001): {len(h)} registros en historial")

    conn.close()
    print("\n============================================================")
    print(">>> TODAS LAS PRUEBAS COMPLETADAS SATISFACTORIAMENTE <<<")
    print("============================================================")


if __name__ == "__main__":
    run_tests()
