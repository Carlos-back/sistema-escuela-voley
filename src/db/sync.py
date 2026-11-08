"""
Flamingo Sys — Sincronización con la nube (MongoDB Atlas) — HU05, Sprint 5

La base local (SQLite) es la principal y la nube es el respaldo: la
sincronización es de una sola vía, local -> nube.

Cómo funciona:
  1. Triggers de SQLite anotan en SyncLog cada alta o modificación de las
     tablas sincronizadas (ver db.database.TABLAS_SINCRONIZADAS).
  2. sincronizar() toma solo los cambios pendientes, lee la versión actual de
     cada registro y la sube con upsert por clave primaria.
  3. Un cambio se marca como sincronizado recién cuando la nube confirmó la
     escritura. Si se corta a mitad de camino, lo que faltó queda pendiente
     y el reintento no duplica nada (el upsert es idempotente).
"""

from pymongo.errors import ConfigurationError
import datetime
import json
import os
import socket
import threading

from config.config import Config
from db.database import TABLAS_SINCRONIZADAS, get_connection

SYNC_LOG_PATH = os.path.join(os.path.dirname(Config.DB_PATH), "sync_log.json")
MSG_SIN_CONEXION = "Sin conexión, los cambios quedan pendientes"
MSG_SIN_CONFIGURAR = "No hay una base de datos en la nube configurada (MONGODB_URI)."

# Tamaño de lote para leer registros y escribir en la nube
TAMANIO_LOTE = 500

# Evita dos sincronizaciones a la vez (la automática y la manual)
_lock = threading.Lock()


# ══════════════════════════════════════════════════════════════════
# Conexión
# ══════════════════════════════════════════════════════════════════
MSG_URI_INVALIDA = ("No se encontró el cluster de MongoDB Atlas. Revisá que MONGODB_URI "
                    "en el archivo .env sea la cadena de conexión real del cluster")


def verificar_conexion():
    """
    True si hay una URI configurada y conexión a internet. Se prueba un
    socket al DNS de Google (3 s), más rápido que esperar el timeout de Mongo.
    """
    if not Config.MONGODB_URI:
        return False
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3).close()
        return True
    except OSError:
        return False


def _crear_cliente():
    """Cliente de MongoDB Atlas. Aislado en una función para poder probarlo."""
    import pymongo
    return pymongo.MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=5000)


# ══════════════════════════════════════════════════════════════════
# Estado
# ══════════════════════════════════════════════════════════════════
def contar_pendientes():
    """Cantidad de registros con cambios todavía no subidos a la nube."""
    conn = get_connection()
    if not conn:
        return 0
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM (SELECT DISTINCT tabla_afectada, id_registro "
            "FROM SyncLog WHERE sincronizado = 0)").fetchone()[0]
    finally:
        conn.close()


def obtener_ultima_sincronizacion():
    """Fecha y hora de la última sincronización exitosa, o 'Nunca sincronizado'."""
    if not os.path.exists(SYNC_LOG_PATH):
        return "Nunca sincronizado"
    try:
        with open(SYNC_LOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("ultima_exitosa") or "Nunca sincronizado"
    except Exception:
        return "Nunca sincronizado"


def _guardar_log_local(resultado):
    """Guarda el resultado en disco conservando la fecha de la última sync exitosa."""
    anterior = {}
    if os.path.exists(SYNC_LOG_PATH):
        try:
            with open(SYNC_LOG_PATH, "r", encoding="utf-8") as f:
                anterior = json.load(f)
        except Exception:
            anterior = {}
    data = dict(resultado)
    data["ultima_exitosa"] = (resultado["fecha"] if resultado.get("exito")
                              else anterior.get("ultima_exitosa")
                              or (anterior.get("fecha") if anterior.get("exito") else None))
    try:
        with open(SYNC_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error guardando log local: {e}")


# ══════════════════════════════════════════════════════════════════
# Sincronización
# ══════════════════════════════════════════════════════════════════
def _pendientes_por_tabla(conn):
    """{tabla: {id_registro: [ids de SyncLog]}} de los cambios no sincronizados."""
    pendientes = {}
    for fila in conn.execute(
            "SELECT id, tabla_afectada, id_registro FROM SyncLog WHERE sincronizado = 0"):
        tabla = fila["tabla_afectada"]
        if tabla not in TABLAS_SINCRONIZADAS:
            continue
        pendientes.setdefault(tabla, {}).setdefault(fila["id_registro"], []).append(fila["id"])
    return pendientes


def _lotes(lista, tamanio):
    for i in range(0, len(lista), tamanio):
        yield lista[i:i + tamanio]


def _subir_tabla(conn, db_cloud, tabla, cambios):
    """
    Sube a la nube la versión actual de los registros modificados de una tabla
    y marca sus entradas de SyncLog como sincronizadas, lote por lote.
    Retorna la cantidad de registros subidos.
    """
    from pymongo import UpdateOne

    pk = TABLAS_SINCRONIZADAS[tabla]
    coleccion = db_cloud[tabla.lower()]
    subidos = 0
    for ids in _lotes(list(cambios), TAMANIO_LOTE):
        marcadores = ",".join("?" * len(ids))
        filas = [dict(r) for r in conn.execute(
            f"SELECT * FROM {tabla} WHERE {pk} IN ({marcadores})", ids)]
        if filas:
            coleccion.bulk_write(
                [UpdateOne({pk: f[pk]}, {"$set": f}, upsert=True) for f in filas],
                ordered=False)
            subidos += len(filas)

        # Recién con la escritura confirmada se marcan como sincronizados
        log_ids = [log_id for i in ids for log_id in cambios[i]]
        for lote in _lotes(log_ids, TAMANIO_LOTE):
            conn.execute(
                f"UPDATE SyncLog SET sincronizado = 1 WHERE id IN ({','.join('?' * len(lote))})",
                lote)
        conn.commit()
    return subidos


def sincronizar(automatica=False):
    """
    Sube a MongoDB Atlas solo los registros nuevos o modificados desde la
    última sincronización.

    Retorna un dict: {fecha, exito, automatica, registros_sincronizados,
                      tablas_sincronizadas, pendientes, sin_conexion, error}
    """
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    resultado = {"fecha": ahora, "exito": False, "automatica": automatica,
                 "registros_sincronizados": 0, "tablas_sincronizadas": [],
                 "sin_conexion": False, "error": None}

    if not _lock.acquire(blocking=False):
        resultado.update(error="Ya hay una sincronización en curso.",
                         pendientes=contar_pendientes())
        return resultado

    conn = client = None
    try:
        if not Config.MONGODB_URI:
            resultado.update(error=MSG_SIN_CONFIGURAR, sin_conexion=True)
            return resultado
        if not verificar_conexion():
            resultado.update(error=MSG_SIN_CONEXION, sin_conexion=True)
            return resultado

        conn = get_connection()
        pendientes = _pendientes_por_tabla(conn)
        if pendientes:
            client = _crear_cliente()
            db_cloud = client[Config.MONGO_DB_NAME]
            for tabla, cambios in pendientes.items():
                resultado["registros_sincronizados"] += _subir_tabla(
                    conn, db_cloud, tabla, cambios)
                resultado["tablas_sincronizadas"].append(tabla.lower())

            registro_nube = {k: v for k, v in resultado.items() if k != "error"}
            registro_nube["exito"] = True
            try:
                db_cloud["sync_log"].insert_one(registro_nube)
            except Exception as e:
                print(f"Advertencia: no se pudo guardar el log en la nube: {e}")

        resultado["exito"] = True
        return resultado
    except ConfigurationError as e:
        # URI mal armada o cluster inexistente (por ejemplo, la URI de ejemplo
        # "cluster.mongodb.net" que viene en .env.example).
        resultado["error"] = f"{MSG_URI_INVALIDA} ({e})"
        return resultado
    except Exception as e:
        resultado["error"] = str(e)
        return resultado
    finally:
        if conn:
            conn.close()
        if client:
            client.close()
        resultado["pendientes"] = contar_pendientes()
        if resultado["exito"] or not resultado["sin_conexion"]:
            _guardar_log_local(resultado)
        _lock.release()
