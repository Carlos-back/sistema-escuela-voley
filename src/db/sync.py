import pymongo
from pymongo.errors import ConnectionFailure, OperationFailure
from config.config import Config
from db.database import get_connection

def is_online():
    """Verifica si hay conexión a MongoDB Atlas."""
    if not Config.MONGODB_URI:
        return False
    try:
        client = pymongo.MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=2000)
        client.admin.command('ping')
        return True
    except (ConnectionFailure, OperationFailure):
        return False

def sync_data():
    """
    Sincroniza los datos locales (SQLite) con la nube (MongoDB Atlas).
    Sube todos los registros de las tablas principales.
    """
    if not is_online():
        print("Sincronización abortada: sin conexión a internet.")
        return False

    try:
        conn = get_connection()
        client = pymongo.MongoClient(Config.MONGODB_URI)
        db_cloud = client[Config.MONGO_DB_NAME]
        
        tablas = ['Grupos', 'Alumnos', 'Pagos', 'Asistencias', 'Usuarios']
        
        for tabla in tablas:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {tabla}")
            rows = cursor.fetchall()
            
            if not rows:
                continue
                
            # Convertir filas a lista de dicts
            data = [dict(row) for row in rows]
            
            # Upsert en MongoDB (usando el ID de SQLite como referencia)
            collection = db_cloud[tabla.lower()]
            
            # Definir el campo ID de SQLite
            id_field = f"id_{tabla[:-1].lower()}" if tabla != 'Asistencias' else 'id_asistencia'
            if tabla == 'Usuarios': id_field = 'id_usuario'
            
            for item in data:
                collection.update_one(
                    {id_field: item[id_field]},
                    {"$set": item},
                    upsert=True
                )
                
        print("Sincronización completada exitosamente.")
        return True
    except Exception as e:
        print(f"Error durante la sincronización: {e}")
        return False
    finally:
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    sync_data()
