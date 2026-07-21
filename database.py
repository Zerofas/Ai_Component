import sqlite3
from datetime import datetime
from typing import Optional, Tuple, Any

DB_NAME = "monitor_precios.db"


def inicializar_db() -> None:
    """
    Configura el esquema relacional. Establece índices en campos de búsqueda
    frecuente (spec técnica y fecha) para optimizar lecturas analíticas del pipeline ETL.
    """
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS precios_hardware (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria_spec TEXT NOT NULL,
            producto_exacto TEXT NOT NULL,
            tienda TEXT NOT NULL,
            precio REAL NOT NULL,
            fecha DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Creación de índice compuesto para optimizar agregaciones temporales
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_spec_fecha 
        ON precios_hardware (categoria_spec, fecha DESC);
    """)

    conexion.commit()
    conexion.close()
    print(f"[DB INFO] Esquema relacional e índices verificados en base de datos local: {DB_NAME}")


def insertar_precio(spec: str, producto: str, tienda: str, precio: float) -> None:
    """
    Persiste un registro de precio aplicando consultas parametrizadas (?)
    para mitigar vulnerabilidades de inyección SQL y mantener atomicidad.

    Args:
        spec: Categoría o especificación técnica del hardware.
        producto: Nombre exacto del modelo extraído.
        tienda: Nombre del comercio o distribuidor.
        precio: Valor numérico del precio del producto.
    """
    try:
        conexion = sqlite3.connect(DB_NAME)
        cursor = conexion.cursor()

        cursor.execute("""
            INSERT INTO precios_hardware (categoria_spec, producto_exacto, tienda, precio, fecha)
            VALUES (?, ?, ?, ?, ?)
        """, (spec, producto, tienda, float(precio), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        conexion.commit()
        conexion.close()
        print(f"[DB EXEC] Persistencia exitosa -> [{spec}] guardado a {precio:.2f} EUR.")
    except Exception as e:
        print(f"[DB ERROR] Fallo de escritura transaccional en SQLite: {e}")


def obtener_chollo_por_categoria(spec: str, horas_ventana: int = 24) -> Optional[Tuple[str, float, str, str]]:
    """
    Recupera el registro con el precio mínimo absoluto registrado dentro
    de una ventana temporal móvil (por defecto 24 horas).

    Args:
        spec: Categoría o especificación técnica a consultar.
        horas_ventana: Tiempo hacia atrás en horas para evaluar el mínimo.

    Returns:
        Tupla con (producto_exacto, precio, tienda, fecha) o None si no hay registros.
    """
    conexion = sqlite3.connect(DB_NAME)
    cursor = conexion.cursor()

    # Consulta optimizada mediante motor de base de datos usando función agregada MIN
    cursor.execute("""
        SELECT producto_exacto, precio, tienda, fecha 
        FROM precios_hardware 
        WHERE categoria_spec = ? 
          AND datetime(fecha) >= datetime('now', '-' || ? || ' hours', 'localtime')
        ORDER BY precio ASC 
        LIMIT 1
    """, (spec, str(horas_ventana)))

    resultado = cursor.fetchone()
    conexion.close()
    return resultado