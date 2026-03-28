import sqlite3

def setup_db():
    conn = sqlite3.connect('gimnasio.db') 
    cursor = conn.cursor() 
    
    # 1. Tabla de usuarios (Login)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # 2. Tabla de miembros (ACTUALIZADA: Agregamos usa_locker)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS miembros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellidos TEXT NOT NULL,
            telefono TEXT UNIQUE NOT NULL,
            telefono_emergencia TEXT,
            email TEXT,
            enfermedad TEXT NOT NULL, 
            detalles_enfermedad TEXT,
            tipo_plan TEXT NOT NULL,
            usa_locker TEXT NOT NULL, 
            fecha_registro DATE NOT NULL,
            fecha_vencimiento DATE NOT NULL,
            estatus TEXT NOT NULL,
            huella_id TEXT
        )
    ''')

    # 3. Catálogo de Planes y Precios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS planes_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            costo REAL NOT NULL,
            dias_duracion INTEGER NOT NULL
        )
    ''')
    
    # 4. NUEVA TABLA: Configuración General del Gimnasio
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_gym TEXT NOT NULL,
            costo_locker REAL NOT NULL
        )
    ''')
    
    # --- POBLAR DATOS POR DEFECTO SI ESTÁ VACÍO ---
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO usuarios (username, password) VALUES ('admin', 'admin123')")
        
    cursor.execute("SELECT COUNT(*) FROM planes_config")
    if cursor.fetchone()[0] == 0:
        planes_default = [
            ('Primera Visita', 0.0, 1),
            ('Visita', 50.0, 1),
            ('Semana', 150.0, 7),
            ('Mensualidad', 400.0, 30),
            ('Anualidad', 4000.0, 365)
        ]
        cursor.executemany("INSERT INTO planes_config (nombre, costo, dias_duracion) VALUES (?, ?, ?)", planes_default)

    # Inyectar configuración por defecto
    cursor.execute("SELECT COUNT(*) FROM configuracion")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO configuracion (nombre_gym, costo_locker) VALUES (?, ?)", ("Gochi's GYM", 50.0))
        
    # 5. NUEVA TABLA: Historial de Pagos y Caja
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            miembro_id INTEGER,
            concepto TEXT NOT NULL,
            monto REAL NOT NULL,
            metodo_pago TEXT NOT NULL,
            fecha_hora DATETIME NOT NULL
        )
    ''')
    conn.commit() 
    conn.close()