"""
Flamingo Sys — Sincronización con la nube (MongoDB Atlas) — HU05, Sprint 5

Sincronización en dos sentidos: cada equipo sube sus cambios a la nube y baja
los que cargaron los demás equipos.

Cómo funciona:
  1. Identidad global. Cada registro sincronizado tiene un uuid, igual en
     todos los equipos y en la nube (los id numéricos son locales: cada equipo
     numera distinto). Las claves foráneas viajan como uuid del padre.
     Alumnos (DNI), Usuarios (usuario) y Grupos (nombre) usan un uuid derivado
     de su dato natural, así el mismo alumno cargado en dos equipos es un solo
     registro en la nube y no un duplicado.
  2. Bajada. Se traen los documentos que otros equipos escribieron desde la
     última bajada (marca de tiempo del servidor, sync_ts) y se aplican en la
     base local. Mientras se aplican, los triggers no anotan cambios, así lo
     bajado no se vuelve a subir.
  3. Subida. Triggers de SQLite anotan en SyncLog cada alta o modificación;
     se sube solo lo pendiente con upsert por uuid. Un cambio se marca como
     sincronizado recién cuando la nube confirmó la escritura: si se corta a
     mitad de camino, lo que faltó queda pendiente y el reintento no duplica.
  4. Conflictos. Si el mismo registro se modificó en dos equipos, gana el
     cambio más reciente (fecha de modificación). Si un dato bajado choca con
     una regla local (por ejemplo, dos inscripciones vigentes del mismo alumno
     en el período), no se aplica y se informa como conflicto.
"""

import datetime
import json
import os
import socket
import sqlite3
import threading
import uuid as uuidlib

from pymongo.errors import ConfigurationError

from config.config import Config
from db.database import (CLAVES_FORANEAS, TABLAS_SINCRONIZADAS, get_connection,
                         normalizar_texto)

SYNC_LOG_PATH = os.path.join(os.path.dirname(Config.DB_PATH), "sync_log.json")
MSG_SIN_CONEXION = "Sin conexión, los cambios quedan pendientes"
MSG_SIN_CONFIGURAR = "No hay una base de datos en la nube configurada (MONGODB_URI)."
MSG_URI_INVALIDA = ("No se encontró el cluster de MongoDB Atlas. Revisá que MONGODB_URI "
                    "en el archivo .env sea la cadena de conexión real del cluster")

# Tamaño de lote para leer registros y escribir en la nube
TAMANIO_LOTE = 500

# Margen al pedir cambios a la nube, por escrituras que se confirman casi a la
# vez que la bajada anterior. Aplicar dos veces lo mismo no cambia nada.
MARGEN_BAJADA = datetime.timedelta(minutes=2)

# Espacio de nombres para los uuid derivados de un dato natural
NAMESPACE = uuidlib.UUID("6f1c2a9e-3b7d-4c55-9a0e-f1a3e5c7b901")

# Campos que agrega la nube y no son columnas locales
CAMPOS_NUBE = {"_id", "uuid", "sync_ts", "modificado_en", "origen"}

# Evita dos sincronizaciones a la vez (la automática y la manual)
_lock = threading.Lock()


# ══════════════════════════════════════════════════════════════════
# Conexión
# ══════════════════════════════════════════════════════════════════
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
    return pymongo.MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=5000,
                               tz_aware=False)


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
            json.dump(data, f, indent=4, ensure_ascii=False, default=str)
    except Exception as e:
        print(f"Error guardando log local: {e}")


def _leer_estado(conn, clave):
    fila = conn.execute("SELECT valor FROM SyncEstado WHERE clave = ?", (clave,)).fetchone()
    return fila[0] if fila else None


def _guardar_estado(conn, clave, valor):
    conn.execute("INSERT OR REPLACE INTO SyncEstado (clave, valor) VALUES (?, ?)",
                 (clave, valor))


def _id_equipo(conn):
    """Identificador de este equipo, para no bajar lo que subió él mismo."""
    equipo = _leer_estado(conn, "equipo")
    if not equipo:
        equipo = str(uuidlib.uuid4())
        _guardar_estado(conn, "equipo", equipo)
        conn.commit()
    return equipo


# ══════════════════════════════════════════════════════════════════
# Identidad global (uuid)
# ══════════════════════════════════════════════════════════════════
def _uuid_natural(*partes):
    return str(uuidlib.uuid5(NAMESPACE, "|".join(str(p) for p in partes)))


def _uuid_para(conn, tabla, fila):
    """
    uuid de un registro nuevo. Los que tienen un dato natural único usan un
    uuid derivado de él, así dos equipos que cargan lo mismo coinciden.
    """
    if tabla == "Alumnos":
        return _uuid_natural("alumno", fila["dni"].strip())
    if tabla == "Usuarios":
        return _uuid_natural("usuario", fila["usuario"].strip().lower())
    if tabla == "Grupos":
        return _uuid_natural("grupo", normalizar_texto(fila["nombre_grupo"].strip()))
    if tabla == "PreguntasSeguridad":
        return _uuid_natural("preguntas", _uuid_de(conn, "Usuarios", fila["id_usuario"]))
    if tabla == "Pagos":
        return _uuid_natural("pago", _uuid_de(conn, "Alumnos", fila["id_alumno"]), fila["mes"])
    if tabla == "Asistencias":
        return _uuid_natural("asistencia", _uuid_de(conn, "Alumnos", fila["id_alumno"]),
                             fila["fecha_clase"])
    return str(uuidlib.uuid4())


def _uuid_de(conn, tabla, id_local):
    pk = TABLAS_SINCRONIZADAS[tabla]
    fila = conn.execute(f"SELECT uuid FROM {tabla} WHERE {pk} = ?", (id_local,)).fetchone()
    return fila[0] if fila else None


def _id_local(conn, tabla, uuid):
    pk = TABLAS_SINCRONIZADAS[tabla]
    fila = conn.execute(f"SELECT {pk} FROM {tabla} WHERE uuid = ?", (uuid,)).fetchone()
    return fila[0] if fila else None


def _asignar_uuids(conn):
    """
    Da uuid a los registros que todavía no tienen (los recién creados).
    Va en orden de tablas para que los padres tengan uuid antes que los hijos.
    El UPDATE dispara el trigger, así que quedan pendientes de subir.
    """
    conn.execute("BEGIN")
    for tabla, pk in TABLAS_SINCRONIZADAS.items():
        filas = conn.execute(f"SELECT * FROM {tabla} WHERE uuid IS NULL").fetchall()
        for fila in filas:
            nuevo = _uuid_para(conn, tabla, fila)
            # Si el uuid natural ya lo usa otro registro (dato natural repetido,
            # por ejemplo dos grupos con el mismo nombre) se usa uno aleatorio.
            if conn.execute(f"SELECT 1 FROM {tabla} WHERE uuid = ?", (nuevo,)).fetchone():
                nuevo = str(uuidlib.uuid4())
            conn.execute(f"UPDATE {tabla} SET uuid = ? WHERE {pk} = ?", (nuevo, fila[pk]))
    conn.commit()


# ══════════════════════════════════════════════════════════════════
# Subida
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


def _fecha_cambio_local(conn, tabla, id_registro):
    """Fecha (UTC) del último cambio local pendiente de un registro, o None."""
    fila = conn.execute(
        "SELECT MAX(fecha_operacion) FROM SyncLog WHERE tabla_afectada = ? "
        "AND id_registro = ? AND sincronizado = 0", (tabla, id_registro)).fetchone()
    return fila[0] if fila else None


def _a_documento(conn, tabla, fila, equipo):
    """Fila local -> documento de la nube (sin id locales, con uuid)."""
    pk = TABLAS_SINCRONIZADAS[tabla]
    doc = {k: v for k, v in dict(fila).items() if k != pk}
    for columna, tabla_padre in CLAVES_FORANEAS.get(tabla, {}).items():
        doc[f"{columna}_uuid"] = _uuid_de(conn, tabla_padre, doc.pop(columna))
    doc["modificado_en"] = (_fecha_cambio_local(conn, tabla, fila[pk])
                            or datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
    doc["origen"] = equipo
    return doc


def _subir_tabla(conn, db_cloud, tabla, cambios, equipo):
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
        filas = conn.execute(
            f"SELECT * FROM {tabla} WHERE {pk} IN ({marcadores})", ids).fetchall()
        operaciones = [
            UpdateOne({"uuid": f["uuid"]},
                      {"$set": _a_documento(conn, tabla, f, equipo),
                       "$currentDate": {"sync_ts": True}},
                      upsert=True)
            for f in filas if f["uuid"]]
        if operaciones:
            coleccion.bulk_write(operaciones, ordered=False)
            subidos += len(operaciones)

        # Recién con la escritura confirmada se marcan como sincronizados
        log_ids = [log_id for i in ids for log_id in cambios[i]]
        for lote in _lotes(log_ids, TAMANIO_LOTE):
            conn.execute(
                f"UPDATE SyncLog SET sincronizado = 1 WHERE id IN ({','.join('?' * len(lote))})",
                lote)
        conn.commit()
    return subidos


# ══════════════════════════════════════════════════════════════════
# Bajada
# ══════════════════════════════════════════════════════════════════
def _columnas(conn, tabla):
    return [c[1] for c in conn.execute(f"PRAGMA table_info({tabla})")]


def _aplicar_documento(conn, tabla, doc, columnas):
    """
    Aplica en la base local un documento bajado de la nube.
    Retorna "aplicado", "omitido" (el cambio local es más nuevo) o lanza
    sqlite3.IntegrityError / ValueError si choca con una regla local.
    """
    pk = TABLAS_SINCRONIZADAS[tabla]
    datos = {k: v for k, v in doc.items() if k in columnas and k not in CAMPOS_NUBE
             and k != pk}

    for columna, tabla_padre in CLAVES_FORANEAS.get(tabla, {}).items():
        uuid_padre = doc.get(f"{columna}_uuid")
        id_padre = _id_local(conn, tabla_padre, uuid_padre) if uuid_padre else None
        if id_padre is None:
            raise ValueError(f"falta el registro relacionado en {tabla_padre}")
        datos[columna] = id_padre

    id_existente = _id_local(conn, tabla, doc["uuid"])
    if id_existente is not None:
        actual = conn.execute(f"SELECT * FROM {tabla} WHERE {pk} = ?",
                              (id_existente,)).fetchone()
        if all(actual[c] == v for c, v in datos.items()):
            return "sin_cambios"   # ya estaba igual (por ejemplo, bajado antes)
        cambio_local = _fecha_cambio_local(conn, tabla, id_existente)
        if cambio_local and cambio_local > (doc.get("modificado_en") or ""):
            return "omitido"   # gana el cambio local, se sube después
        asignaciones = ", ".join(f"{c} = ?" for c in datos)
        conn.execute(f"UPDATE {tabla} SET {asignaciones} WHERE {pk} = ?",
                     [*datos.values(), id_existente])
        # El cambio local quedó reemplazado por uno más nuevo de la nube
        conn.execute("UPDATE SyncLog SET sincronizado = 1 WHERE tabla_afectada = ? "
                     "AND id_registro = ? AND sincronizado = 0", (tabla, id_existente))
    else:
        datos["uuid"] = doc["uuid"]
        conn.execute(f"INSERT INTO {tabla} ({', '.join(datos)}) "
                     f"VALUES ({', '.join('?' * len(datos))})", list(datos.values()))
    return "aplicado"


def _describir(tabla, doc):
    if tabla == "Alumnos":
        return f"alumno {doc.get('apellido')}, {doc.get('nombre')} (DNI {doc.get('dni')})"
    if tabla == "Inscripciones":
        return f"inscripción del período {doc.get('periodo')}"
    if tabla == "Grupos":
        return f"grupo {doc.get('nombre_grupo')}"
    if tabla == "Usuarios":
        return f"usuario {doc.get('usuario')}"
    return f"registro de {tabla}"


def _bajar_cambios(conn, db_cloud, equipo, resultado):
    """
    Trae de la nube lo que escribieron otros equipos desde la última bajada y
    lo aplica en la base local. Retorna la nueva marca de tiempo de bajada.
    """
    marca = _leer_estado(conn, "ultima_bajada")
    filtro = {"uuid": {"$exists": True}, "origen": {"$ne": equipo}}
    if marca:
        filtro["sync_ts"] = {"$gt": datetime.datetime.fromisoformat(marca) - MARGEN_BAJADA}

    nueva_marca = marca
    for tabla in TABLAS_SINCRONIZADAS:   # en orden: padres antes que hijos
        columnas = _columnas(conn, tabla)
        bajados = 0
        for doc in db_cloud[tabla.lower()].find(filtro).sort("sync_ts", 1):
            conn.execute("SAVEPOINT registro")
            try:
                estado = _aplicar_documento(conn, tabla, doc, columnas)
                conn.execute("RELEASE registro")
                if estado == "aplicado":
                    bajados += 1
            except (sqlite3.IntegrityError, ValueError) as e:
                conn.execute("ROLLBACK TO registro")
                conn.execute("RELEASE registro")
                resultado["conflictos"].append(f"No se aplicó {_describir(tabla, doc)}: {e}")
            ts = doc.get("sync_ts")
            if ts and (not nueva_marca or ts.isoformat() > nueva_marca):
                nueva_marca = ts.isoformat()
        if bajados:
            resultado["registros_descargados"] += bajados
            resultado["tablas_descargadas"].append(tabla.lower())
    return nueva_marca


def _bajar(conn, db_cloud, equipo, resultado):
    """Aplica la bajada en una sola transacción, con los triggers en pausa."""
    conn.execute("BEGIN")
    try:
        _guardar_estado(conn, "aplicando_descarga", "1")
        nueva_marca = _bajar_cambios(conn, db_cloud, equipo, resultado)
        conn.execute("DELETE FROM SyncEstado WHERE clave = 'aplicando_descarga'")
        if nueva_marca:
            _guardar_estado(conn, "ultima_bajada", nueva_marca)
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# ══════════════════════════════════════════════════════════════════
# Sincronización
# ══════════════════════════════════════════════════════════════════
def sincronizar(automatica=False):
    """
    Baja de MongoDB Atlas los cambios de los otros equipos y sube los
    registros nuevos o modificados de este equipo.

    Retorna un dict: {fecha, exito, automatica, registros_sincronizados,
                      tablas_sincronizadas, registros_descargados,
                      tablas_descargadas, conflictos, pendientes,
                      sin_conexion, error}
    """
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    resultado = {"fecha": ahora, "exito": False, "automatica": automatica,
                 "registros_sincronizados": 0, "tablas_sincronizadas": [],
                 "registros_descargados": 0, "tablas_descargadas": [],
                 "conflictos": [], "sin_conexion": False, "error": None}

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
        conn.isolation_level = None   # transacciones manejadas a mano
        equipo = _id_equipo(conn)
        _asignar_uuids(conn)

        client = _crear_cliente()
        db_cloud = client[Config.MONGO_DB_NAME]

        # 1) Bajar primero: si un registro cambió en los dos lados, el más
        #    nuevo gana y la subida no pisa algo más reciente de la nube.
        _bajar(conn, db_cloud, equipo, resultado)

        # 2) Subir lo pendiente de este equipo
        pendientes = _pendientes_por_tabla(conn)
        for tabla, cambios in pendientes.items():
            conn.execute("BEGIN")
            resultado["registros_sincronizados"] += _subir_tabla(
                conn, db_cloud, tabla, cambios, equipo)
            resultado["tablas_sincronizadas"].append(tabla.lower())

        if resultado["registros_sincronizados"] or resultado["registros_descargados"]:
            registro_nube = {k: v for k, v in resultado.items() if k != "error"}
            registro_nube.update(exito=True, origen=equipo)
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
            if conn.in_transaction:
                conn.rollback()
            conn.close()
        if client:
            client.close()
        resultado["pendientes"] = contar_pendientes()
        if resultado["exito"] or not resultado["sin_conexion"]:
            _guardar_log_local(resultado)
        _lock.release()
