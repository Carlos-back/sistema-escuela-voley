import sqlite3
import os
from config.config import Config

def get_connection():
    """Retorna una conexión a la base de datos SQLite."""
    try:
        conn = sqlite3.connect(Config.DB_PATH)
        # Habilitar claves foráneas
        conn.execute("PRAGMA foreign_keys = ON;")
        # Tiempo de espera para bases de datos bloqueadas
        conn.execute("PRAGMA busy_timeout = 5000;")
        # Modo WAL para mejor concurrencia
        conn.execute("PRAGMA journal_mode = WAL;")
        # Retornar filas como diccionarios
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Error conectando a SQLite: {e}")
        return None

def _migrar_grupos(conn, cursor):
    """
    Reconstruye la tabla Grupos si conserva el esquema viejo
    (CHECK fijo sobre nombre_grupo y/o sin columna 'estado').
    SQLite no permite eliminar un CHECK con ALTER TABLE, por lo que se
    crea una tabla nueva, se copian los datos y se renombra.
    """
    row = cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='Grupos'"
    ).fetchone()
    if not row:
        return

    # Normalizamos sin espacios para detectar el CHECK específico de nombre_grupo
    sql_norm = (row[0] or "").upper().replace(" ", "")
    cols = [c[1] for c in cursor.execute("PRAGMA table_info(Grupos)").fetchall()]

    tiene_check_viejo = "CHECK(NOMBRE_GRUPO" in sql_norm
    falta_estado = "estado" not in cols

    if not (tiene_check_viejo or falta_estado):
        return  # Ya está migrada

    # Desactivar FK para poder dropear/renombrar sin romper Alumnos.id_grupo
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF;")
    cursor.executescript("""
        CREATE TABLE Grupos_new (
          id_grupo INTEGER PRIMARY KEY AUTOINCREMENT,
          nombre_grupo TEXT NOT NULL,
          horario TEXT NOT NULL,
          descripcion TEXT,
          estado TEXT NOT NULL DEFAULT 'activo' CHECK(estado IN ('activo', 'inactivo'))
        );
        INSERT INTO Grupos_new (id_grupo, nombre_grupo, horario, descripcion, estado)
          SELECT id_grupo, nombre_grupo, horario, descripcion, 'activo' FROM Grupos;
        DROP TABLE Grupos;
        ALTER TABLE Grupos_new RENAME TO Grupos;
    """)
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON;")
    print("Migración de Grupos completada (nombre libre + columna estado).")


def init_db():
    """Inicializa la base de datos creando las tablas si no existen."""
    conn = get_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Crear tablas
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS Grupos (
      id_grupo INTEGER PRIMARY KEY AUTOINCREMENT,
      nombre_grupo TEXT NOT NULL,
      horario TEXT NOT NULL,
      descripcion TEXT,
      estado TEXT NOT NULL DEFAULT 'activo' CHECK(estado IN ('activo', 'inactivo'))
    );

    CREATE TABLE IF NOT EXISTS Alumnos (
      id_alumno INTEGER PRIMARY KEY AUTOINCREMENT,
      nombre TEXT NOT NULL,
      apellido TEXT NOT NULL,
      dni TEXT NOT NULL UNIQUE,
      fecha_nacimiento TEXT NOT NULL,
      telefono TEXT,
      telefono_tutor TEXT,
      direccion TEXT,
      fecha_inscripcion TEXT NOT NULL DEFAULT (date('now')),
      estado TEXT NOT NULL DEFAULT 'activo' CHECK(estado IN ('activo', 'inactivo')),
      id_grupo INTEGER NOT NULL,
      FOREIGN KEY (id_grupo) REFERENCES Grupos(id_grupo) ON UPDATE CASCADE ON DELETE RESTRICT
    );

    CREATE TABLE IF NOT EXISTS Pagos (
      id_pago INTEGER PRIMARY KEY AUTOINCREMENT,
      id_alumno INTEGER NOT NULL,
      mes TEXT NOT NULL,
      monto REAL NOT NULL CHECK(monto >= 0),
      fecha_pago TEXT,
      metodo_pago TEXT CHECK(metodo_pago IN ('efectivo', 'transferencia')),
      estado TEXT NOT NULL DEFAULT 'adeuda' CHECK(estado IN ('pagado', 'adeuda')),
      FOREIGN KEY (id_alumno) REFERENCES Alumnos(id_alumno) ON UPDATE CASCADE ON DELETE RESTRICT,
      UNIQUE (id_alumno, mes)
    );

    CREATE TABLE IF NOT EXISTS Asistencias (
      id_asistencia INTEGER PRIMARY KEY AUTOINCREMENT,
      id_alumno INTEGER NOT NULL,
      fecha_clase TEXT NOT NULL,
      estado TEXT NOT NULL CHECK(estado IN ('presente', 'ausente')),
      FOREIGN KEY (id_alumno) REFERENCES Alumnos(id_alumno) ON UPDATE CASCADE ON DELETE RESTRICT,
      UNIQUE (id_alumno, fecha_clase)
    );

    CREATE TABLE IF NOT EXISTS Usuarios (
      id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
      usuario TEXT NOT NULL UNIQUE,
      contrasena TEXT NOT NULL,
      rol TEXT NOT NULL CHECK(rol IN ('administrador', 'profesor')),
      nombre TEXT,
      apellido TEXT,
      email TEXT,
      activo INTEGER DEFAULT 1 -- 1: activo, 0: inactivo
    );

    CREATE TABLE IF NOT EXISTS PreguntasSeguridad (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      id_usuario INTEGER NOT NULL,
      pregunta_1 TEXT NOT NULL,
      respuesta_1 TEXT NOT NULL,
      pregunta_2 TEXT NOT NULL,
      respuesta_2 TEXT NOT NULL,
      pregunta_3 TEXT NOT NULL,
      respuesta_3 TEXT NOT NULL,
      FOREIGN KEY (id_usuario) REFERENCES Usuarios(id_usuario) ON UPDATE CASCADE ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS Movimientos (
      id_movimiento INTEGER PRIMARY KEY AUTOINCREMENT,
      tipo TEXT NOT NULL CHECK(tipo IN ('ingreso', 'egreso')),
      monto REAL NOT NULL CHECK(monto >= 0),
      descripcion TEXT NOT NULL,
      fecha TEXT NOT NULL DEFAULT (date('now')),
      categoria TEXT
    );

    CREATE TABLE IF NOT EXISTS Insumos (
      id_insumo INTEGER PRIMARY KEY AUTOINCREMENT,
      nombre TEXT NOT NULL,
      cantidad INTEGER NOT NULL DEFAULT 0,
      minimo_stock INTEGER DEFAULT 5,
      descripcion TEXT
    );
    
    -- Tabla para control de sincronización
    CREATE TABLE IF NOT EXISTS SyncLog (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tabla_afectada TEXT NOT NULL,
        id_registro INTEGER NOT NULL,
        operacion TEXT NOT NULL, -- 'INSERT', 'UPDATE', 'DELETE'
        fecha_operacion DATETIME DEFAULT CURRENT_TIMESTAMP,
        sincronizado INTEGER DEFAULT 0 -- 0: no, 1: sí
    );

    -- Tabla de auditoría (registro de acciones de los usuarios)
    CREATE TABLE IF NOT EXISTS Auditoria (
        id_auditoria INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        accion TEXT NOT NULL,          -- 'INSERT', 'UPDATE', 'DELETE'
        entidad TEXT NOT NULL,         -- ej. 'Grupos'
        id_entidad INTEGER,
        datos TEXT,                    -- snapshot en JSON
        fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # --- MIGRACIÓN Grupos: quitar CHECK fijo del nombre y agregar 'estado' ---
    # SQLite no permite DROP de un CHECK con ALTER; se reconstruye la tabla.
    _migrar_grupos(conn, cursor)

    # Insertar grupos por defecto si no existen
    cursor.execute("SELECT COUNT(*) FROM Grupos")
    if cursor.fetchone()[0] == 0:
        grupos = [
            ('Infantil', 'Lunes y Miércoles 18:00', 'De 6 a 12 años'),
            ('Juvenil', 'Martes y Jueves 19:00', 'De 13 a 17 años'),
            ('Adultos', 'Lunes a Viernes 20:30', 'Más de 18 años')
        ]
        cursor.executemany("INSERT INTO Grupos (nombre_grupo, horario, descripcion) VALUES (?, ?, ?)", grupos)
    
    # --- NUEVAS COLUMNAS (MIGREACION DINAMICA) ---
    def add_column_if_missing(table, column, type_definition):
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {type_definition}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                print(f"Error migrando {table}.{column}: {e}")
            
    add_column_if_missing("Usuarios", "nombre", "TEXT")
    add_column_if_missing("Usuarios", "apellido", "TEXT")
    add_column_if_missing("Usuarios", "email", "TEXT")
    add_column_if_missing("Usuarios", "activo", "INTEGER DEFAULT 1")
    
    conn.commit()
    conn.close()
    print("Base de datos inicializada correctamente.")

if __name__ == "__main__":
    init_db()
