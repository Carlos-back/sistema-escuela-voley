import socket
import datetime
import json
import os
import pymongo
from pymongo.errors import ConnectionFailure, OperationFailure
from config.config import Config
from db.database import get_connection

SYNC_LOG_PATH = os.path.join(os.path.dirname(Config.DB_PATH), "sync_log.json")

def verificar_conexion():
    """
    Verifica si hay conexión a internet haciendo ping al DNS de Google (8.8.8.8)
    mediante sockets. Es mucho más rápido que esperar un timeout de MongoDB.
    """
    if not Config.MONGODB_URI:
        return False
    try:
        # Timeout corto de 3 segundos
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        pass
    return False

def obtener_ultima_sincronizacion():
    """Retorna un string con la fecha y hora de la última sincronización."""
    if not os.path.exists(SYNC_LOG_PATH):
        return "Nunca sincronizado"
    try:
        with open(SYNC_LOG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if data and data.get("exito"):
                return data.get("fecha", "Desconocida")
    except Exception:
        pass
    return "Nunca sincronizado"

def _guardar_log_local(log_data):
    """Guarda el registro de la sincronización en disco."""
    try:
        with open(SYNC_LOG_PATH, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error guardando log local: {e}")

def sincronizar():
    """
    Sincroniza los datos locales (SQLite) con la nube (MongoDB Atlas).
    Sube todos los registros de las tablas principales y PreguntasSeguridad.
    Retorna un diccionario con el resultado.
    """
    ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if not verificar_conexion():
        log_data = {
            "fecha": ahora,
            "exito": False,
            "error": "Sin conexión, intente más tarde"
        }
        return log_data

    conn = None
    client = None
    try:
        conn = get_connection()
        client = pymongo.MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=5000)
        db_cloud = client[Config.MONGO_DB_NAME]
        
        tablas = ['Grupos', 'Alumnos', 'Pagos', 'Asistencias', 'Usuarios', 'PreguntasSeguridad']
        registros_totales = 0
        tablas_sync = []
        
        for tabla in tablas:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {tabla}")
            rows = cursor.fetchall()
            
            if not rows:
                continue
                
            data = [dict(row) for row in rows]
            collection = db_cloud[tabla.lower()]
            
            # Determinar campo ID para la colección actual
            id_field = f"id_{tabla[:-1].lower()}" if tabla not in ['Asistencias', 'PreguntasSeguridad'] else 'id_asistencia'
            if tabla == 'Usuarios': id_field = 'id_usuario'
            if tabla == 'PreguntasSeguridad': id_field = 'id'  # La tabla PreguntasSeguridad tiene id primary key
            
            # Upsert
            for item in data:
                collection.update_one(
                    {id_field: item[id_field]},
                    {"$set": item},
                    upsert=True
                )
            
            registros_totales += len(data)
            tablas_sync.append(tabla.lower())
            
        log_data = {
            "fecha": ahora,
            "exito": True,
            "tablas_sincronizadas": tablas_sync,
            "registros_sincronizados": registros_totales,
            "error": None
        }
        
        # Guardar log en local
        _guardar_log_local(log_data)
        
        # Guardar log en MongoDB Atlas
        try:
            db_cloud["sync_log"].insert_one(log_data.copy())
        except Exception as e_mongo:
            print(f"Advertencia: no se pudo guardar el log en MongoDB: {e_mongo}")
            
        return log_data
        
    except Exception as e:
        log_data = {
            "fecha": ahora,
            "exito": False,
            "error": str(e)
        }
        _guardar_log_local(log_data)
        return log_data
    finally:
        if conn: conn.close()
        if client: client.close()
