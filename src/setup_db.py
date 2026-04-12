import os
import sys

# Agregar src al path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from db.database import init_db
from services.usuarios import crear_usuario

def setup():
    print("Inicializando base de datos...")
    init_db()
    
    print("Creando usuario administrador por defecto...")
    # usuario: admin, contrasena: admin123, rol: administrador
    exito = crear_usuario(
        usuario="admin", 
        contrasena="admin123", 
        rol="administrador",
        nombre="Administrador",
        apellido="Sistema",
        email="admin@flamingo.com"
    )
    
    if exito:
        print("Usuario 'admin' creado con éxito (pass: admin123).")
    else:
        print("El usuario administrador ya existe o hubo un error.")

if __name__ == "__main__":
    setup()
