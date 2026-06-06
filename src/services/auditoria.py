"""
Flamingo Sys — Servicio de Auditoría
Registra acciones de los usuarios sobre las entidades del sistema.
"""

import json
from db.database import get_connection


def registrar(accion, entidad, id_entidad=None, datos=None, usuario=None, conn=None):
    """
    Inserta un registro en la tabla Auditoria.

    Parámetros:
        accion     : 'INSERT' | 'UPDATE' | 'DELETE'
        entidad    : nombre de la tabla/entidad afectada (ej. 'Grupos')
        id_entidad : id del registro afectado
        datos      : dict serializable con el snapshot de los datos
        usuario    : identificador del usuario que ejecuta la acción
        conn       : conexión existente. Si se provee, NO se hace commit ni
                     close (el caller maneja la transacción). Si es None, la
                     función abre su propia conexión y la cierra.

    Retorna True/False según éxito.
    """
    datos_json = json.dumps(datos, ensure_ascii=False) if datos is not None else None
    propia = conn is None

    if propia:
        conn = get_connection()
        if not conn:
            return False

    try:
        conn.execute(
            """
            INSERT INTO Auditoria (usuario, accion, entidad, id_entidad, datos)
            VALUES (?, ?, ?, ?, ?)
            """,
            (usuario, accion, entidad, id_entidad, datos_json),
        )
        if propia:
            conn.commit()
        return True
    except Exception as e:
        print(f"Error al registrar auditoría: {e}")
        return False
    finally:
        if propia:
            conn.close()
