import customtkinter as ctk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime, timedelta
import os
from modal_cobro import ModalCobro
import cv2
from PIL import Image
import win32print
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart



class MiembrosFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, corner_radius=10, fg_color="transparent")
        
        # --- VARIABLES DEL FORMULARIO ---
        self.var_id = ctk.StringVar()
        self.var_nombre = ctk.StringVar()
        self.var_apellidos = ctk.StringVar()
        self.var_telefono = ctk.StringVar()
        self.var_emergencia = ctk.StringVar()
        self.var_email = ctk.StringVar()
        self.var_enfermedad = ctk.StringVar(value="") 
        self.var_plan = ctk.StringVar(value="Seleccionar...")
        self.var_locker = ctk.StringVar(value="No") # NUEVA VARIABLE PARA LOCKER
        self.var_estatus = ctk.StringVar(value="Activo")
        self.var_busqueda = ctk.StringVar()
        self.var_anio_mantenimiento = ctk.IntVar(value=0) # Para saber qué año pagó por última vez
        self.monto_mantenimiento_actual = 0.0 # Para guardar el cálculo del prorrateo y pasarlo al ticket

        for var in [self.var_nombre, self.var_apellidos, self.var_telefono, self.var_emergencia, self.var_email, self.var_enfermedad, self.var_plan, self.var_estatus]:
            var.trace_add("write", self.validar_formulario)

        self.vista_lista = ctk.CTkFrame(self, fg_color="transparent")
        self.vista_formulario = ctk.CTkFrame(self, fg_color="transparent")
        
        self.configurar_vista_lista()
        self.configurar_vista_formulario()
        
        self.mostrar_lista()

    def obtener_planes_db(self):
        conn = sqlite3.connect('gimnasio.db')
        cursor = conn.cursor()
        cursor.execute("SELECT nombre FROM planes_config")
        planes = [fila[0] for fila in cursor.fetchall()]
        conn.close()
        return planes

    def obtener_costo_locker(self):
        conn = sqlite3.connect('gimnasio.db')
        cursor = conn.cursor()
        cursor.execute("SELECT costo_locker FROM configuracion LIMIT 1")
        resultado = cursor.fetchone()
        conn.close()
        return resultado[0] if resultado else 0.0

    # ==========================================
    # VISTA 1: LISTA Y BUSCADOR 
    # ==========================================
    def configurar_vista_lista(self):
        top_frame = ctk.CTkFrame(self.vista_lista, fg_color="transparent")
        top_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(top_frame, text="🔍 Buscar:", font=("Arial", 14, "bold")).pack(side="left", padx=(10, 5))
        self.entry_buscar = ctk.CTkEntry(
            top_frame, 
            placeholder_text="Nombre, apellidos, teléfono o estatus...", 
            width=400
        )
        self.entry_buscar.pack(side="left", padx=(0, 10))
        self.entry_buscar.bind('<Return>', self.buscar_miembros) 
        
        btn_nuevo = ctk.CTkButton(top_frame, text="➕ Nuevo Miembro", command=lambda: self.mostrar_formulario())
        btn_nuevo.pack(side="right")
        
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", rowheight=30, font=("Arial", 11))
        style.configure("Treeview.Heading", font=("Arial", 12, "bold"))
        
        columnas = ("id", "nombre", "plan", "estatus", "vencimiento", "restantes")
        self.tabla = ttk.Treeview(self.vista_lista, columns=columnas, show="headings", height=15)
                
        self.tabla.heading("id", text="ID")
        self.tabla.heading("nombre", text="Nombre del Socio")
        self.tabla.heading("plan", text="Tipo de Plan")
        self.tabla.heading("estatus", text="Estatus")
        self.tabla.heading("vencimiento", text="Vencimiento")
        self.tabla.heading("restantes", text="Días Restantes") # NUEVO ENCABEZADO
        
        self.tabla.column("id", width=50, anchor="center")
        self.tabla.column("nombre", width=250)
        self.tabla.column("plan", width=150, anchor="center")
        self.tabla.column("estatus", width=100, anchor="center")
        self.tabla.column("vencimiento", width=120, anchor="center")
        self.tabla.column("restantes", width=120, anchor="center") # NUEVO ANCHO DE COLUMNA
        self.tabla.tag_configure('vigente', foreground='green')
        self.tabla.tag_configure('vencido', foreground='red')
        self.tabla.tag_configure('por_vencer', foreground='#d35400') # Naranja (Alerta)
        self.tabla.tag_configure('inactivo', foreground='gray')
        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind("<Double-1>", self.editar_socio) 
        
        self.lbl_sin_resultados = ctk.CTkLabel(self.vista_lista, text="", text_color="red", font=("Arial", 14))

    def cargar_datos_tabla(self, query="SELECT * FROM miembros", parametros=()):
        for item in self.tabla.get_children():
            self.tabla.delete(item)
            
        conn = sqlite3.connect('gimnasio.db')
        cursor = conn.cursor()
        cursor.execute(query, parametros)
        filas = cursor.fetchall()
        
        hoy = datetime.now().date()
        
        if not filas:
            if self.entry_buscar.get().strip() != "":
                self.lbl_sin_resultados.configure(text="Socio no encontrado.")
                self.lbl_sin_resultados.pack(pady=10)
            else:
                self.lbl_sin_resultados.pack_forget() 
        else:
            self.lbl_sin_resultados.pack_forget()
            # --- DICCIONARIO DE REGLAS DE AVISO ---
            umbrales_aviso = {
                "Primera Visita": 0,
                "Visita": 0,
                "Semana": 2, # Empieza a avisar 2 días antes
                "Mensualidad": 5, # Empieza a avisar 5 días antes
                "Anualidad": 15
            }

            for fila in filas:
                id_socio = fila[0]
                nombre_completo = f"{fila[1]} {fila[2]}"
                plan = fila[8]
                vencimiento_str = fila[11] 
                estatus = fila[12] 
                
                vencimiento_date = datetime.strptime(vencimiento_str, "%Y-%m-%d").date()
                dias_restantes = (vencimiento_date - hoy).days # Cuántos días le quedan
                umbral = umbrales_aviso.get(plan, 0) # Obtenemos la regla según su plan
                
                texto_restante = "-"
                tag = 'inactivo'
                
                if estatus == "Activo":
                    if dias_restantes < 0:
                        # REGLA 1: Se le acabó el tiempo. Pasa a Inactivo inmediatamente.
                        cursor.execute("UPDATE miembros SET estatus='Inactivo' WHERE id=?", (id_socio,))
                        conn.commit()
                        estatus = "Inactivo"
                        tag = 'inactivo'
                        texto_restante = "Vencido"
                        
                    elif dias_restantes == 0:
                        # REGLA 2: Vence el día de hoy. Súper alerta naranja.
                        tag = 'por_vencer'
                        texto_restante = "Vence HOY"
                        
                    elif dias_restantes <= umbral:
                        # REGLA 3: Entró en su periodo de prevención (Ej. le quedan 3 días al de Mensualidad)
                        tag = 'por_vencer'
                        texto_restante = f"{dias_restantes} días"
                        
                    else:
                        # REGLA 4: Está sobrado de tiempo (Verde)
                        tag = 'vigente'
                        texto_restante = f"{dias_restantes} días"
                else:
                    # Si ya estaba Inactivo por otra razón
                    tag = 'inactivo'
                    texto_restante = "Inactivo"
                        
                # Insertamos la fila en la tabla
                self.tabla.insert("", "end", values=(id_socio, nombre_completo, plan, estatus, vencimiento_str, texto_restante), tags=(tag,))
        conn.close()

    def buscar_miembros(self, event=None):
        termino = f"%{self.entry_buscar.get().strip()}%"
        query = "SELECT * FROM miembros WHERE nombre LIKE ? OR apellidos LIKE ? OR telefono LIKE ? OR estatus LIKE ?"
        self.cargar_datos_tabla(query, (termino, termino, termino, termino))

    # ==========================================
    # VISTA 2: FORMULARIO 
    # ==========================================
    def configurar_vista_formulario(self):
        frame_top = ctk.CTkFrame(self.vista_formulario, fg_color="transparent")
        frame_top.pack(fill="x", pady=10, padx=20)
        ctk.CTkButton(frame_top, text="⬅ Volver a la lista", fg_color="gray", command=self.mostrar_lista).pack(side="left")
        
        self.lbl_titulo_form = ctk.CTkLabel(self.vista_formulario, text="Registrar Nuevo Socio", font=("Arial", 24, "bold"))
        self.lbl_titulo_form.pack(pady=(0, 20))

        contenedor_central = ctk.CTkFrame(self.vista_formulario, fg_color="transparent")
        contenedor_central.pack(expand=True)

        form_grid = ctk.CTkFrame(contenedor_central, fg_color="transparent")
        form_grid.pack(pady=10)

        self.lbl_estatus = ctk.CTkLabel(form_grid, text="Estatus del Socio:")
        self.combo_estatus = ctk.CTkComboBox(form_grid, values=["Activo", "Inactivo"], variable=self.var_estatus, command=self.validar_cambio_estatus)

        ctk.CTkLabel(form_grid, text="Nombre *").grid(row=1, column=0, sticky="w", pady=5)
        self.entry_nombre = ctk.CTkEntry(form_grid, textvariable=self.var_nombre, width=250)
        self.entry_nombre.grid(row=1, column=1, sticky="w", padx=(0, 20), pady=5)
        self.err_nombre = ctk.CTkLabel(form_grid, text="", text_color="red", font=("Arial", 10))
        self.err_nombre.grid(row=2, column=1, sticky="w")

        ctk.CTkLabel(form_grid, text="Apellidos *").grid(row=1, column=2, sticky="w", pady=5)
        self.entry_apellidos = ctk.CTkEntry(form_grid, textvariable=self.var_apellidos, width=250)
        self.entry_apellidos.grid(row=1, column=3, sticky="w", pady=5)
        self.err_apellidos = ctk.CTkLabel(form_grid, text="", text_color="red", font=("Arial", 10))
        self.err_apellidos.grid(row=2, column=3, sticky="w")

        ctk.CTkLabel(form_grid, text="Teléfono *").grid(row=3, column=0, sticky="w", pady=5)
        self.entry_telefono = ctk.CTkEntry(form_grid, textvariable=self.var_telefono, width=250)
        self.entry_telefono.grid(row=3, column=1, sticky="w", padx=(0, 20), pady=5)
        self.err_telefono = ctk.CTkLabel(form_grid, text="", text_color="red", font=("Arial", 10))
        self.err_telefono.grid(row=4, column=1, sticky="w")

        ctk.CTkLabel(form_grid, text="Tel. Emergencia").grid(row=3, column=2, sticky="w", pady=5)
        self.entry_emergencia = ctk.CTkEntry(form_grid, textvariable=self.var_emergencia, width=250)
        self.entry_emergencia.grid(row=3, column=3, sticky="w", pady=5)

        ctk.CTkLabel(form_grid, text="Email").grid(row=5, column=0, sticky="w", pady=5)
        self.entry_email = ctk.CTkEntry(form_grid, textvariable=self.var_email, width=250)
        self.entry_email.grid(row=5, column=1, sticky="w", padx=(0, 20), pady=5)

        ctk.CTkLabel(form_grid, text="Tipo de Plan *").grid(row=5, column=2, sticky="w", pady=5)
        self.combo_plan = ctk.CTkComboBox(form_grid, values=["Seleccionar..."], variable=self.var_plan, width=250, command=self.actualizar_costo_plan)
        self.combo_plan.grid(row=5, column=3, sticky="w", pady=5)
        
        # NUEVO: Fila 6 para el Locker y el Costo Total
        self.switch_locker = ctk.CTkSwitch(form_grid, text="Añadir Locker (+ Costo Extra)", variable=self.var_locker, onvalue="Si", offvalue="No", state="disabled", command=lambda: self.actualizar_costo_plan(self.var_plan.get()))
        self.switch_locker.grid(row=6, column=2, sticky="w", pady=5)

        self.lbl_costo_plan = ctk.CTkLabel(form_grid, text="", font=("Arial", 12, "bold"))
        self.lbl_costo_plan.grid(row=6, column=3, sticky="w")

        self.err_plan = ctk.CTkLabel(form_grid, text="", text_color="red", font=("Arial", 10))
        self.err_plan.grid(row=7, column=3, sticky="w")

        ctk.CTkLabel(form_grid, text="¿Enfermedad/Lesión? *").grid(row=8, column=0, sticky="w", pady=5)
        frame_radio = ctk.CTkFrame(form_grid, fg_color="transparent")
        frame_radio.grid(row=8, column=1, sticky="w", pady=5)
        ctk.CTkRadioButton(frame_radio, text="Sí", variable=self.var_enfermedad, value="Si", command=self.toggle_enfermedad).pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(frame_radio, text="No", variable=self.var_enfermedad, value="No", command=self.toggle_enfermedad).pack(side="left")
        self.err_enf = ctk.CTkLabel(form_grid, text="", text_color="red", font=("Arial", 10))
        self.err_enf.grid(row=9, column=1, sticky="w")

        ctk.CTkLabel(form_grid, text="Detalles:").grid(row=8, column=2, sticky="nw", pady=5)
        self.txt_detalles = ctk.CTkTextbox(form_grid, width=250, height=60, state="disabled")
        self.txt_detalles.grid(row=8, column=3, sticky="w", pady=5)
        # --- NUEVA SECCIÓN: ESTUDIO FOTOGRÁFICO ---
        # Lo ponemos en la columna 4 para que quede a la derecha de todo el formulario
        frame_foto = ctk.CTkFrame(form_grid, fg_color="transparent")
        frame_foto.grid(row=1, column=4, rowspan=8, padx=(30, 0), sticky="n")

        self.lbl_video = ctk.CTkLabel(frame_foto, text="Cámara Apagada", width=200, height=200, fg_color="#2c3e50", corner_radius=10)
        self.lbl_video.pack(pady=(0, 10))
        self.lbl_estado_foto = ctk.CTkLabel(frame_foto, text="", font=("Arial", 12, "bold"))
        self.lbl_estado_foto.pack(pady=(0, 5))

        self.btn_encender_cam = ctk.CTkButton(frame_foto, text="📷 Encender Cámara", command=self.iniciar_camara, width=180)
        self.btn_encender_cam.pack(pady=5)

        self.btn_tomar_foto = ctk.CTkButton(frame_foto, text="📸 Capturar Foto", command=self.tomar_foto, state="disabled", fg_color="#d35400", hover_color="#e67e22", width=180)
        self.btn_tomar_foto.pack(pady=5)
        
        # Variable para guardar la ruta en la base de datos después
        self.ruta_foto_actual = ""
        self.captura = None 
        # ----------------------------------------

        frame_acciones = ctk.CTkFrame(contenedor_central, fg_color="transparent")
        frame_acciones.pack(pady=(20, 5))

        self.btn_cancelar = ctk.CTkButton(frame_acciones, text="Cancelar", fg_color="gray", hover_color="#555555", command=self.mostrar_lista, height=40, width=150)
        self.btn_cancelar.pack(side="left", padx=10)

        self.btn_guardar = ctk.CTkButton(frame_acciones, text="Guardar Socio", state="disabled", command=self.guardar_socio, height=40, width=150)
        self.btn_guardar.pack(side="left", padx=10)
        
        self.lbl_error_bd = ctk.CTkLabel(contenedor_central, text="", text_color="red", font=("Arial", 12, "bold"))
        self.lbl_error_bd.pack()

    # ==========================================
    # LÓGICA DE NEGOCIO 
    # ==========================================
    def actualizar_costo_plan(self, valor_seleccionado):
        # 1. CANDADO DEL LOCKER
        if valor_seleccionado in ["Mensualidad", "Anualidad"]:
            self.switch_locker.configure(state="normal")
        else:
            self.var_locker.set("No")
            self.switch_locker.configure(state="disabled")

        if valor_seleccionado == "Seleccionar...":
            self.lbl_costo_plan.configure(text="")
            self.monto_mantenimiento_actual = 0.0
            return

        # 2. CONSULTAR COSTOS EN BD (BLINDADO)
        try:
            conn = sqlite3.connect('gimnasio.db')
            cursor = conn.cursor()
            cursor.execute("SELECT costo FROM planes_config WHERE nombre=?", (valor_seleccionado,))
            res_plan = cursor.fetchone()

            try:
                cursor.execute("SELECT costo_locker, costo_mantenimiento FROM configuracion LIMIT 1")
                res_config = cursor.fetchone()
                costo_mantenimiento_db = res_config[1] if res_config and len(res_config) > 1 else 0.0
            except sqlite3.OperationalError:
                cursor.execute("SELECT costo_locker FROM configuracion LIMIT 1")
                res_config = cursor.fetchone()
                costo_mantenimiento_db = 0.0

            conn.close()
        except Exception as e:
            print(f"Error al consultar BD: {e}")
            return

        costo_base = res_plan[0] if res_plan else 0.0
        costo_locker_db = res_config[0] if res_config else 0.0
        costo_locker = costo_locker_db if self.var_locker.get() == "Si" else 0.0
        self.monto_mantenimiento_actual = 0.0

        # --- 3. LÓGICA DE MANTENIMIENTO ANUAL (REGLA DEL DÍA 1) ---
        hoy = datetime.now()
        
        # Validamos el "sello" del año. Si la variable falla o no existe, asumimos que no ha pagado (False).
        try:
            mantenimiento_pagado = self.var_anio_mantenimiento.get() >= hoy.year
        except AttributeError:
            mantenimiento_pagado = False 

        if not mantenimiento_pagado:
            if valor_seleccionado == "Anualidad":
                # Regla: Anualidad paga el 100% SIEMPRE
                self.monto_mantenimiento_actual = costo_mantenimiento_db
                
            elif valor_seleccionado == "Mensualidad":
                # Regla: Mensualidad paga el prorrateo del mes actual hasta Diciembre
                meses_restantes = 12 - hoy.month + 1
                self.monto_mantenimiento_actual = (costo_mantenimiento_db / 12) * meses_restantes
            else:
                # Visitas, Cortesías o planes casuales se salvan
                self.monto_mantenimiento_actual = 0.0
        else:
            # Si ya pagó el año actual, lo dejamos en paz
            self.monto_mantenimiento_actual = 0.0

        # --- 4. CALCULAR TOTAL Y MOSTRAR DESGLOSE ---
        costo_total = costo_base + costo_locker + self.monto_mantenimiento_actual

        if costo_base == 0:
            self.lbl_costo_plan.configure(text="¡Cortesía! Costo: $0.00 MXN", text_color="#2ecc71")
        else:
            texto_desglose = f"Plan: ${costo_base:.2f}"
            if costo_locker > 0:
                texto_desglose += f" | Locker: ${costo_locker:.2f}"
            if self.monto_mantenimiento_actual > 0:
                texto_desglose += f" | Mant: ${self.monto_mantenimiento_actual:.2f}"
                
            texto_desglose += f"\nTotal: ${costo_total:.2f} MXN"
            
            self.lbl_costo_plan.configure(text=texto_desglose, text_color="white")
            
            if self.var_id.get() != "": 
                self.var_estatus.set("Activo")

    def mostrar_lista(self):
        self.apagar_camara() # Aseguramos apagar la cámara si estaba encendida
        self.vista_formulario.pack_forget()
        self.vista_lista.pack(fill="both", expand=True)
        self.entry_buscar.delete(0, "end") 
        self.cargar_datos_tabla()

    def mostrar_formulario(self, id_socio=None):
        self.vista_lista.pack_forget()
        self.vista_formulario.pack(fill="both", expand=True)
        self.lbl_error_bd.configure(text="") 
        
        planes_disponibles = self.obtener_planes_db()

        # ---> NUEVO: LIMPIEZA DE MEMORIA (LAVADO DE CEREBRO) <---
        self.apagar_camara()
        self.ruta_foto_actual = ""
        # Si existe una imagen cargada en memoria, la borramos
        if hasattr(self, 'imagen_actual_tk'):
            del self.imagen_actual_tk
        # Regresamos el recuadro a su estado original (gris y sin foto)
        self.lbl_video.configure(image="", text="Cámara Apagada", require_redraw=True)
        self.lbl_estado_foto.configure(text="")
        self.btn_encender_cam.configure(state="normal", text="📷 Encender Cámara")
        self.btn_tomar_foto.configure(state="disabled")
        # --------------------------------------------------------
        
        if id_socio is None:
            self.lbl_titulo_form.configure(text="Registrar Nuevo Socio")
            self.btn_guardar.configure(text="Guardar Socio")
            self.var_anio_mantenimiento.set(0) # <--- NUEVA LÍNEA: Reiniciamos la memoria del año
            self.lbl_estatus.grid_remove()
            self.combo_estatus.grid_remove()
            
            planes_disponibles.insert(0, "Seleccionar...")
            self.combo_plan.configure(values=planes_disponibles)
            
            for var in [self.var_id, self.var_nombre, self.var_apellidos, self.var_telefono, self.var_emergencia, self.var_email]:
                var.set("")
            self.var_enfermedad.set("")
            self.var_plan.set("Seleccionar...")
            self.var_locker.set("No") # Reiniciar locker
            self.switch_locker.configure(state="disabled")
            self.lbl_costo_plan.configure(text="") 
            self.txt_detalles.configure(state="normal")
            self.txt_detalles.delete("1.0", "end")
            self.txt_detalles.configure(state="disabled")
        else:
            self.lbl_titulo_form.configure(text="Modificar Socio")
            self.btn_guardar.configure(text="Actualizar Socio")
            self.lbl_estatus.grid(row=0, column=0, sticky="w", pady=(0, 15))
            self.combo_estatus.grid(row=0, column=1, sticky="w", pady=(0, 15))
            
            if "Primera Visita" in planes_disponibles:
                planes_disponibles.remove("Primera Visita")
            planes_disponibles.insert(0, "Seleccionar...")
            self.combo_plan.configure(values=planes_disponibles)
            
            self.cargar_datos_socio(id_socio)

    def toggle_enfermedad(self):
        if self.var_enfermedad.get() == "Si":
            self.txt_detalles.configure(state="normal")
        else:
            self.txt_detalles.configure(state="normal")
            self.txt_detalles.delete("1.0", "end")
            self.txt_detalles.configure(state="disabled")
        self.validar_formulario()

    def validar_cambio_estatus(self, valor):
        if valor == "Inactivo":
            id_socio = self.var_id.get()
            if id_socio:
                conn = sqlite3.connect('gimnasio.db')
                cursor = conn.cursor()
                cursor.execute("SELECT fecha_vencimiento FROM miembros WHERE id=?", (id_socio,))
                res = cursor.fetchone()
                conn.close()
                if res:
                    vencimiento = datetime.strptime(res[0], "%Y-%m-%d").date()
                    if vencimiento >= datetime.now().date():
                        respuesta = messagebox.askyesno("Advertencia", "Plan del socio en vigencia, ¿estás seguro de que deseas inactivarlo?")
                        if not respuesta:
                            self.var_estatus.set("Activo") 

    def validar_formulario(self, *args):
        es_valido = True
        
        nombre = self.var_nombre.get()
        if len(nombre) > 50: self.var_nombre.set(nombre[:50])
        if not nombre.strip():
            self.err_nombre.configure(text="El nombre no puede estar en blanco")
            es_valido = False
        elif any(char.isdigit() for char in nombre):
            self.err_nombre.configure(text="Solo se permiten letras")
            es_valido = False
        else:
            self.err_nombre.configure(text="")

        apellidos = self.var_apellidos.get()
        if len(apellidos) > 50: self.var_apellidos.set(apellidos[:50])
        if not apellidos.strip():
            self.err_apellidos.configure(text="Los apellidos son obligatorios")
            es_valido = False
        else:
            self.err_apellidos.configure(text="")

        tel = self.var_telefono.get()
        if len(tel) > 12: self.var_telefono.set(tel[:12])
        if not tel.strip():
            self.err_telefono.configure(text="Teléfono obligatorio")
            es_valido = False
        elif not tel.isdigit():
            self.err_telefono.configure(text="Solo números permitidos")
            es_valido = False
        else:
            self.err_telefono.configure(text="")

        if self.var_enfermedad.get() not in ["Si", "No"]:
            self.err_enf.configure(text="Seleccione una opción")
            es_valido = False
        else:
            self.err_enf.configure(text="")

        if self.var_plan.get() == "Seleccionar...":
            self.err_plan.configure(text="Debe seleccionar un plan")
            es_valido = False
        else:
            self.err_plan.configure(text="")

        if es_valido:
            self.btn_guardar.configure(state="normal")
        else:
            self.btn_guardar.configure(state="disabled")

    def guardar_socio(self):
        conn = sqlite3.connect('gimnasio.db')
        cursor = conn.cursor()
        
        id_actual = self.var_id.get()
        if id_actual: 
            cursor.execute("SELECT id FROM miembros WHERE telefono=? AND id!=?", (self.var_telefono.get(), id_actual))
        else: 
            cursor.execute("SELECT id FROM miembros WHERE telefono=?", (self.var_telefono.get(),))
            
        if cursor.fetchone():
            self.lbl_error_bd.configure(text="Error: Este teléfono ya existe.")
            conn.close()
            return
            
        plan = self.var_plan.get()
        cursor.execute("SELECT costo FROM planes_config WHERE nombre=?", (plan,))
        res_plan = cursor.fetchone()
        monto_plan = res_plan[0] if res_plan else 0.0
        
        monto_locker = 0.0
        if self.var_locker.get() == "Si":
            cursor.execute("SELECT costo_locker FROM configuracion LIMIT 1")
            res_locker = cursor.fetchone()
            if res_locker:
                monto_locker = res_locker[0]

        # --- LÓGICA DE UMBRALES DE RENOVACIÓN ---
        es_renovacion = True
        if id_actual:
            cursor.execute("SELECT tipo_plan, fecha_vencimiento, usa_locker FROM miembros WHERE id=?", (id_actual,))
            res_actual = cursor.fetchone()
            if res_actual:
                plan_bd = res_actual[0]
                venc_bd = datetime.strptime(res_actual[1], "%Y-%m-%d").date()
                locker_bd = res_actual[2]
                hoy = datetime.now().date()
                
                # Definimos los días de anticipación permitidos para renovar
                umbrales = {
                    "Mensualidad": 5,
                    "Anualidad": 15,
                    "Semana": 1,
                    "Visita": 0
                }
                
                umbral = umbrales.get(plan, 0)
                dias_restantes = (venc_bd - hoy).days
                
                # REGLA: Si es el mismo plan y faltan MÁS días que el umbral, no cobramos (es solo edición)
                if plan == plan_bd and dias_restantes > umbral:
                    monto_plan = 0.0
                
                # Regla del Locker: Si ya lo tenía y no ha cambiado el estatus, no cobramos
                if self.var_locker.get() == "Si" and locker_bd == "Si":
                    # Solo cobramos el locker si el plan también se está renovando
                    if monto_plan == 0.0:
                        monto_locker = 0.0
                
                if monto_plan == 0.0 and monto_locker == 0.0:
                    es_renovacion = False

        conn.close()
        
        # El total de la operación incluye el mantenimiento si es que aplica
        total_operacion = monto_plan + monto_locker + self.monto_mantenimiento_actual

        if total_operacion > 0:
            total_plan_y_mant = monto_plan + self.monto_mantenimiento_actual
            ModalCobro(self.winfo_toplevel(), total_plan_y_mant, monto_locker, self.ejecutar_guardado_bd)
        else:
            motivo = "Actualización" if id_actual and not es_renovacion else "Cortesía"
            self.ejecutar_guardado_bd(motivo, "0", 0.0, 0.0)

    def enviar_correo_background(self, concepto, monto, nombre_cliente, plan):
        # Esta función corre en su propio carril invisible
        try:
            remitente = "notificacionessportlife@gmail.com" # El correo que crees para el gym
            password = "klcccpcccuzwkyue" # Ojo, no es tu password normal
            destinatario = "angelgomez140994@gmail.com"

            # 1. Armamos la carta
            mensaje = MIMEMultipart()
            mensaje['From'] = remitente
            mensaje['To'] = destinatario
            mensaje['Subject'] = f"Notificación de Caja: {concepto}"

            cuerpo = f"""
            Hola Administrador,
            Se ha registrado un nuevo movimiento en caja:
            
            Cliente: {nombre_cliente}
            Operación: {concepto}
            Plan: {plan}
            Total Cobrado: ${monto} MXN
            
            Este es un mensaje automático del Sistema ERP.
            """
            mensaje.attach(MIMEText(cuerpo, 'plain'))

            # 2. Vamos al buzón de Google y la mandamos
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls() # Encriptamos la conexión
            server.login(remitente, password)
            text = mensaje.as_string()
            server.sendmail(remitente, destinatario, text)
            server.quit()
            
            print("Correo enviado al admin exitosamente (Background).")
            
        except Exception as e:
            # Si falla (no hay internet o la contraseña está mal), choca aquí en silencio
            # sin destruir el programa principal de la recepcionista.
            print(f"Error silencioso al enviar correo: {e}")


    def ejecutar_guardado_bd(self, metodo_pago, monto_recibido, monto_plan, monto_locker):
        conn = sqlite3.connect('gimnasio.db')
        cursor = conn.cursor()
        
        id_actual = self.var_id.get()
        hoy = datetime.now().date()
        plan = self.var_plan.get()
        vencimiento = None
        
        # --- NUEVO: DEFINIR EL CONCEPTO EXACTO PARA EL TICKET Y CORREO ---
        if metodo_pago == "Cortesía":
            concepto_venta = "Cortesía (Visita Gratis)"
        elif id_actual:
            concepto_venta = "Renovación de Membresía"
        else:
            concepto_venta = "Nueva Membresía"
            
        total_pagado = monto_plan + monto_locker
        
        if id_actual:
            cursor.execute("SELECT tipo_plan, fecha_vencimiento, ruta_foto FROM miembros WHERE id=?", (id_actual,))
            res_actual = cursor.fetchone()
            if res_actual:
                plan_bd = res_actual[0]
                venc_bd = datetime.strptime(res_actual[1], "%Y-%m-%d").date()
                foto_bd = res_actual[2]
                
                # --- NUEVA LÓGICA DE VENCIMIENTO ---
                if metodo_pago == "Actualización":
                    # Si solo es edición de datos, mantenemos la fecha actual del socio
                    vencimiento = venc_bd
                else:
                    # Es un cobro/renovación. Obtenemos la duración del plan
                    cursor.execute("SELECT dias_duracion FROM planes_config WHERE nombre=?", (plan,))
                    dias = cursor.fetchone()[0]
                    
                    # Si el socio ya está vencido, empezamos a contar desde HOY
                    # Si aún está vigente, sumamos los días a su fecha de vencimiento actual (acumulativo)
                    if venc_bd < hoy or plan != plan_bd:
                        vencimiento = hoy + timedelta(days=dias)
                    else:
                        vencimiento = venc_bd + timedelta(days=dias)
                
                foto_final = self.ruta_foto_actual if self.ruta_foto_actual != "" else foto_bd
        else:
            foto_final = self.ruta_foto_actual

        # Si es un socio nuevo (no tiene id_actual)
        if vencimiento is None:
            cursor.execute("SELECT dias_duracion FROM planes_config WHERE nombre=?", (plan,))
            res_plan = cursor.fetchone()
            dias = res_plan[0] if res_plan else 30
            vencimiento = hoy if dias <= 1 else hoy + timedelta(days=dias)
        detalles_enf = self.txt_detalles.get("1.0", "end-1c")
        usa_locker = self.var_locker.get()
        anio_a_guardar = datetime.now().year if self.monto_mantenimiento_actual > 0 else self.var_anio_mantenimiento.get()

        try:
            if id_actual:
                cursor.execute('''UPDATE miembros SET 
                            nombre=?, apellidos=?, telefono=?, telefono_emergencia=?, email=?, 
                            enfermedad=?, detalles_enfermedad=?, tipo_plan=?, usa_locker=?, fecha_vencimiento=?, estatus=?,
                            ruta_foto=?, anio_mantenimiento=?
                            WHERE id=?''', 
                            (self.var_nombre.get(), self.var_apellidos.get(), self.var_telefono.get(), 
                            self.var_emergencia.get(), self.var_email.get(), self.var_enfermedad.get(), 
                            detalles_enf, plan, usa_locker, vencimiento.strftime("%Y-%m-%d"), self.var_estatus.get(), 
                            foto_final, anio_a_guardar, id_actual))
                id_para_pago = id_actual
            else:
                cursor.execute('''INSERT INTO miembros 
                            (nombre, apellidos, telefono, telefono_emergencia, email, enfermedad, detalles_enfermedad, tipo_plan, usa_locker, fecha_registro, fecha_vencimiento, estatus, ruta_foto, anio_mantenimiento)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                            (self.var_nombre.get(), self.var_apellidos.get(), self.var_telefono.get(), 
                            self.var_emergencia.get(), self.var_email.get(), self.var_enfermedad.get(), 
                            detalles_enf, plan, usa_locker, hoy.strftime("%Y-%m-%d"), vencimiento.strftime("%Y-%m-%d"), "Activo",
                            foto_final, anio_a_guardar))
                id_para_pago = cursor.lastrowid
            
            # --- TICKETS, PAGOS Y NOTIFICACIONES INTELIGENTES ---
            # Si NO es solo una actualización de datos (es decir, hubo dinero o fue cortesía)
            if metodo_pago != "Actualización":
                fecha_hora_exacta = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Registramos en la 'bóveda' de pagos, incluyendo las cortesías de $0.0
                cursor.execute('''INSERT INTO pagos (miembro_id, concepto, monto, metodo_pago, fecha_hora) 
                                  VALUES (?, ?, ?, ?, ?)''',
                               (id_para_pago, concepto_venta, total_pagado, metodo_pago, fecha_hora_exacta))
                
                # Generamos el ticket físico
                nombre_cliente = f"{self.var_nombre.get()} {self.var_apellidos.get()}"
                self.generar_ticket(nombre_cliente, plan, monto_plan, monto_locker, metodo_pago, vencimiento.strftime("%d/%m/%Y"), concepto_venta)
                # --- NUEVO: DISPARAMOS EL CORREO EN SEGUNDO PLANO ---
                hilo_correo = threading.Thread(target=self.enviar_correo_background, args=(concepto_venta, total_pagado, nombre_cliente, plan))
                hilo_correo.start()

                messagebox.showinfo("Éxito", f"Operación registrada: {concepto_venta}\nTicket generado.")
            else:
                # Si solo entró aquí para cambiar la foto o el teléfono, no genera registro en pagos
                messagebox.showinfo("Éxito", "Datos del socio actualizados correctamente.")
            
            conn.commit()
            self.mostrar_lista()
        except Exception as e:
            self.lbl_error_bd.configure(text="Error al guardar en base de datos.")
            print(f"Error técnico: {e}")
        finally:
            conn.close()

    def generar_ticket(self, nombre_cliente, plan, monto_plan, monto_locker, metodo_pago, fecha_vencimiento, concepto_venta):
        # Esta función crea un archivo .txt con formato de ticket
        fecha_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        total = monto_plan + monto_locker
        
        ticket = f"""
================================
          SportLife GYM           
================================
Fecha: {fecha_hora}
Socio: {nombre_cliente}

>> MOVIMIENTO: {concepto_venta.upper()} <<

--- DESGLOSE DE COMPRA ---
Plan: {plan}
Subtotal Membresia: ${monto_plan:,.2f}
"""
        if self.monto_mantenimiento_actual > 0:
            ticket += f"Mantenimiento Anual: ${self.monto_mantenimiento_actual:,.2f}\n"
        if monto_locker > 0:
            ticket += f"Subtotal Locker:    ${monto_locker:,.2f}\n"

        ticket += f"""--------------------------------
TOTAL A PAGAR:      ${total:,.2f}
Metodo de Pago:     {metodo_pago}
Vencimiento Plan:   {fecha_vencimiento}
--------------------------------

ALERTA Y EXENCION DE RESPONSABILIDAD:
El uso de las instalaciones es bajo su 
propio riesgo. El gimnasio no se hace 
responsable por lesiones, problemas de 
salud o incidentes derivados del uso de 
suplementos, bebidas energeticas o 
sobreesfuerzo fisico. Consulte a su 
medico antes de entrenar.

¡GRACIAS POR TU PREFERENCIA!
================================
"""
        if not os.path.exists("tickets"):
            os.makedirs("tickets")
            
        nombre_archivo = f"tickets/ticket_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Guardamos la ruta absoluta para que Windows no se pierda al imprimir
        ruta_absoluta = os.path.abspath(nombre_archivo)

        with open(ruta_absoluta, "w", encoding="utf-8") as file:
            file.write(ticket)
            
        print(f"Ticket generado en: {ruta_absoluta}")
        
        # --- NUEVA LÓGICA DE IMPRESIÓN FÍSICA ---
        # --- NUEVA LÓGICA DE IMPRESIÓN FÍSICA (MÉTODO RAW) ---
        try:
            impresora_actual = win32print.GetDefaultPrinter()
            print(f"Enviando en formato RAW a: {impresora_actual}")
            
            # 1. Abrimos la conexión directa con el hardware de la impresora
            hPrinter = win32print.OpenPrinter(impresora_actual)
            try:
                # 2. Le indicamos al sistema que le mandaremos bytes crudos (RAW), sin formatos de Windows
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Ticket Gimnasio", "", "RAW"))
                win32print.StartPagePrinter(hPrinter)
                
                # 3. Agregamos saltos de línea al final del ticket. 
                # Esto es VITAL para que el papel avance lo suficiente y puedas cortarlo sin rasgar las letras.
                ticket_final = ticket + "\n\n\n\n\n"
                
                # 4. Convertimos el texto a bytes. 
                # Usamos 'latin-1' (o podrías probar 'cp850') porque es la codificación nativa que 
                # usan la mayoría de estas impresoras para que los acentos y la "ñ" salgan bien.
                datos_crudos = ticket_final.encode("latin-1", errors="replace")
                
                # 5. Disparamos los datos directo a la impresora térmica
                win32print.WritePrinter(hPrinter, datos_crudos)
                
                # 6. Cerramos el trabajo de impresión
                win32print.EndPagePrinter(hPrinter)
                win32print.EndDocPrinter(hPrinter)
            finally:
                # Siempre liberamos la impresora, incluso si hay error
                win32print.ClosePrinter(hPrinter)
                
            print("Ticket impreso correctamente en formato térmico.")
            
        except Exception as e:
            print(f"Error al intentar imprimir físicamente: {e}")
    def editar_socio(self, event):
        item_seleccionado = self.tabla.focus()
        if item_seleccionado:
            valores = self.tabla.item(item_seleccionado, "values")
            id_socio = valores[0]
            self.mostrar_formulario(id_socio)

    def cargar_datos_socio(self, id_socio):
        conn = sqlite3.connect('gimnasio.db')
        cursor = conn.cursor()
        
        # 1. Traemos los datos normales del formulario
        cursor.execute("SELECT * FROM miembros WHERE id=?", (id_socio,))
        fila = cursor.fetchone()
        
        # --- BÚSQUEDA BLINDADA DE FOTO Y MANTENIMIENTO ---
        try:
            cursor.execute("SELECT ruta_foto, anio_mantenimiento FROM miembros WHERE id=?", (id_socio,))
            res_extra = cursor.fetchone()
            ruta_foto_db = res_extra[0] if res_extra and res_extra[0] else ""
            anio_mant_db = int(res_extra[1]) if res_extra and len(res_extra) > 1 and res_extra[1] else 0
        except sqlite3.OperationalError:
            ruta_foto_db = ""
            anio_mant_db = 0
            
        conn.close()
        
        # 1. AQUI ESTÁ LA MAGIA: Guardamos el año antes de evaluar los planes
        self.var_anio_mantenimiento.set(anio_mant_db)

        if fila:
            # Llenamos los campos de texto
            self.var_id.set(fila[0])
            self.var_nombre.set(fila[1])
            self.var_apellidos.set(fila[2])
            self.var_telefono.set(fila[3])
            self.var_emergencia.set(fila[4] if fila[4] else "")
            self.var_email.set(fila[5] if fila[5] else "")
            
            enf = fila[6]
            self.var_enfermedad.set(enf)
            self.toggle_enfermedad()
            if enf == "Si" and fila[7]:
                self.txt_detalles.insert("1.0", fila[7])
                
            plan_guardado = fila[8]
            locker_guardado = fila[9]
            vencimiento_str = fila[11] 
            vencimiento_date = datetime.strptime(vencimiento_str, "%Y-%m-%d").date()
            hoy = datetime.now().date()
            
            # 2. SE ACTUALIZA EL COSTO: Como ya se cargó el año arriba, esto ya saldrá en $0.00
            if plan_guardado == "Primera Visita" and vencimiento_date <= hoy:
                self.var_plan.set("Seleccionar...")
                self.actualizar_costo_plan("Seleccionar...")
            else:
                self.var_plan.set(plan_guardado)
                self.var_locker.set(locker_guardado)
                self.actualizar_costo_plan(plan_guardado)
            
            self.var_estatus.set(fila[12])

            # --- LA MAGIA DE LA FOTO ---
            print("\n--- DEBUG FOTO (BLINDADO) ---")
            print(f"1. ID Socio: {id_socio}")
            print(f"2. Ruta segura encontrada: '{ruta_foto_db}'")
            if ruta_foto_db:
                print(f"3. ¿Existe archivo?: {os.path.exists(ruta_foto_db)}")
            print("-----------------------------\n")
            
            if ruta_foto_db and os.path.exists(ruta_foto_db):
                try:
                    with Image.open(ruta_foto_db) as img_pil:
                        alto, ancho = img_pil.size
                        min_dim = min(alto, ancho)
                        left = (ancho - min_dim) / 2
                        top = (alto - min_dim) / 2
                        right = (ancho + min_dim) / 2
                        bottom = (alto + min_dim) / 2
                        img_recortada = img_pil.crop((left, top, right, bottom))
                        img_recortada = img_recortada.resize((200, 200))
                        
                        self.imagen_actual_tk = ctk.CTkImage(light_image=img_recortada, dark_image=img_recortada, size=(200, 200))
                        
                    self.lbl_video.configure(image=self.imagen_actual_tk, text="", require_redraw=True)
                    self.lbl_estado_foto.configure(text="Foto del Socio", text_color="white")
                    self.btn_encender_cam.configure(text="🔄 Cambiar Foto")

                except Exception as e:
                    print(f"Error al cargar la foto física: {e}")
                    self.lbl_video.configure(image="", text="Error Visual", require_redraw=True)
            else:
                self.lbl_video.configure(image="", text="Socio sin Foto", require_redraw=True)
                self.lbl_estado_foto.configure(text="")
                self.btn_encender_cam.configure(text="📷 Tomar Foto")
            
            self.validar_formulario()
    # ==========================================
    # FUNCIONES DE LA CÁMARA WEB
    # ==========================================
    def iniciar_camara(self):
        # 1. Agregamos cv2.CAP_DSHOW para saltarnos el motor lento de Windows
        self.captura = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        
        if self.captura.isOpened():
            # 2. Forzamos una resolución baja (VGA) al arrancar. 
            # Esto evita que la cámara intente arrancar en 1080p o 4K, haciendo que abra en milisegundos.
            self.captura.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.captura.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            self.btn_encender_cam.configure(state="disabled")
            self.btn_tomar_foto.configure(state="normal")
            self.actualizar_frame()
        else:
            # Si el puerto 1 falla (a veces Windows reasigna los puertos USB), que te avise claro.
            messagebox.showerror("Error", "No se detectó la cámara USB en el puerto 1. Revisa la conexión.")

    def actualizar_frame(self):
        if self.captura and self.captura.isOpened():
            exito, frame = self.captura.read()
            if exito:
                # Convertir los colores de OpenCV (BGR) a colores de Pantalla (RGB)
                cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(cv2image)
                
                # Recortamos la imagen a cuadrado para que se vea estético (como foto de perfil)
                alto, ancho = img.size
                min_dim = min(alto, ancho)
                left = (ancho - min_dim) / 2
                top = (alto - min_dim) / 2
                right = (ancho + min_dim) / 2
                bottom = (alto + min_dim) / 2
                img = img.crop((left, top, right, bottom))
                
                # Redimensionamos al tamaño de nuestro recuadro
                img = img.resize((200, 200))
                
                # La mandamos a CustomTkinter
                self.imagen_actual_tk = ctk.CTkImage(light_image=img, dark_image=img, size=(200, 200))
                self.lbl_video.configure(image=self.imagen_actual_tk, text="")
                
            # Esto es lo que reemplaza al 'while': se llama a sí mismo cada 15 milisegundos
            self.lbl_video.after(15, self.actualizar_frame)

    def tomar_foto(self):
        if self.captura and self.captura.isOpened():
            exito, frame = self.captura.read()
            if exito:
                # 1. Guardamos físicamente en la carpeta
                if not os.path.exists("fotos_socios"):
                    os.makedirs("fotos_socios")
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.ruta_foto_actual = f"fotos_socios/foto_{timestamp}.jpg"
                cv2.imwrite(self.ruta_foto_actual, frame)
                
                self.apagar_camara()
                
                # 2. NUEVO: Forzar el congelamiento visual perfecto en la pantalla
                try:
                    # Convertimos los colores de la cámara para que se vean bien
                    cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img_pil = Image.fromarray(cv2image)
                    
                    # Recortamos a cuadrado exacto
                    alto, ancho = img_pil.size
                    min_dim = min(alto, ancho)
                    left = (ancho - min_dim) / 2
                    top = (alto - min_dim) / 2
                    right = (ancho + min_dim) / 2
                    bottom = (alto + min_dim) / 2
                    img_pil = img_pil.crop((left, top, right, bottom))
                    img_pil = img_pil.resize((200, 200))
                    
                    # Lo pegamos en la interfaz
                    self.imagen_actual_tk = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=(200, 200))
                    self.lbl_video.configure(image=self.imagen_actual_tk, text="", require_redraw=True)
                except Exception as e:
                    print(f"Error al congelar imagen en UI: {e}")

                self.lbl_estado_foto.configure(text="¡Foto Capturada!", text_color="#2ecc71")
                
                
    def apagar_camara(self):
        if self.captura:
            self.captura.release()
            self.captura = None
        self.btn_encender_cam.configure(state="normal")
        self.btn_tomar_foto.configure(state="disabled")