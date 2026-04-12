import sqlite3
import os
import sys

# Agregar src al path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from config.config import Config

def migrate():
    conn = sqlite3.connect(Config.DB_PATH)
    cursor = conn.cursor()
    
    tablas_columnas = {
        "Usuarios": ["nombre", "apellido", "email", "activo"],
    }
    
    for tabla, columnas in tablas_columnas.items():
        for col in columnas:
            try:
                cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {col} TEXT")
                print(f"Columna '{col}' agregada a '{tabla}'.")
            except sqlite3.OperationalError:
                # La columna ya existe
                pass
                
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
