import customtkinter as ctk
from tkinter import ttk, messagebox
import sqlite3

class InventarioFrame(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, corner_radius=10, fg_color="transparent")
        
        # --- VARIABLES DEL FORMULARIO ---
        self.var_id = ctk.StringVar()
        self.var_nombre = ctk.StringVar()
        self.var_cantidad = ctk.StringVar(value="0")
        self.var_costo_compra = ctk.StringVar(value="0.0")
        self.var_costo_venta = ctk.StringVar(value="0.0")

        # Rastrear cambios para validar en tiempo real
        for var in [self.var_nombre, self.var_cantidad, self.var_costo_compra, self.var_costo_venta]:
            var.trace_add("write", self.validar_formulario)

        self.vista_lista = ctk.CTkFrame(self, fg_color="transparent")
        self.vista_formulario = ctk.CTkFrame(self, fg_color="transparent")
        
        self.configurar_vista_lista()
        self.configurar_vista_formulario()
        
        self.mostrar_lista()

    # ==========================================
    # VISTA 1: LISTA Y BUSCADOR 
    # ==========================================
    def configurar_vista_lista(self):
        top_frame = ctk.CTkFrame(self.vista_lista, fg_color="transparent")
        top_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(top_frame, text="🔍 Buscar:", font=("Arial", 14, "bold")).pack(side="left", padx=(10, 5))
        self.entry_buscar = ctk.CTkEntry(
            top_frame, 
            placeholder_text="Nombre del producto...", 
            width=400
        )
        self.entry_buscar.pack(side="left", padx=(0, 10))
        self.entry_buscar.bind('<Return>', self.buscar_productos) 
        
        btn_nuevo = ctk.CTkButton(top_frame, text="➕ Nuevo Producto", command=lambda: self.mostrar_formulario())
        btn_nuevo.pack(side="right")
        
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", rowheight=30, font=("Arial", 11))
        style.configure("Treeview.Heading", font=("Arial", 12, "bold"))
        
        columnas = ("id", "nombre", "cantidad", "costo_compra", "costo_venta")
        self.tabla = ttk.Treeview(self.vista_lista, columns=columnas, show="headings", height=15)
                
        self.tabla.heading("id", text="ID")
        self.tabla.heading("nombre", text="Nombre del Producto")
        self.tabla.heading("cantidad", text="Stock Disponible")
        self.tabla.heading("costo_compra", text="Costo de Compra")
        self.tabla.heading("costo_venta", text="Precio al Público")
        
        self.tabla.column("id", width=50, anchor="center")
        self.tabla.column("nombre", width=300)
        self.tabla.column("cantidad", width=120, anchor="center")
        self.tabla.column("costo_compra", width=120, anchor="center")
        self.tabla.column("costo_venta", width=120, anchor="center")
        
        # --- REGLA DEL COLOR ROJO ---
        self.tabla.tag_configure('sin_stock', foreground='red')
        
        
        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind("<Double-1>", self.editar_producto) 
        
        self.lbl_sin_resultados = ctk.CTkLabel(self.vista_lista, text="", text_color="red", font=("Arial", 14))

    def cargar_datos_tabla(self, query="SELECT * FROM inventario", parametros=()):
        for item in self.tabla.get_children():
            self.tabla.delete(item)
            
        conn = sqlite3.connect('gimnasio.db')
        cursor = conn.cursor()
        cursor.execute(query, parametros)
        filas = cursor.fetchall()
        
        if not filas:
            if self.entry_buscar.get().strip() != "":
                self.lbl_sin_resultados.configure(text="Producto no encontrado.")
                self.lbl_sin_resultados.pack(pady=10)
            else:
                self.lbl_sin_resultados.pack_forget() 
        else:
            self.lbl_sin_resultados.pack_forget()
            
            for fila in filas:
                id_prod = fila[0]
                nombre = fila[1]
                cantidad = fila[2]
                costo_compra = f"${fila[3]:.2f}"
                costo_venta = f"${fila[4]:.2f}"
                
                # Si la cantidad es 0, asignamos el tag rojo
                tag = 'sin_stock' if cantidad == 0 else 'con_stock'
                
                self.tabla.insert("", "end", values=(id_prod, nombre, cantidad, costo_compra, costo_venta), tags=(tag,))
        conn.close()

    def buscar_productos(self, event=None):
        termino = f"%{self.entry_buscar.get().strip()}%"
        query = "SELECT * FROM inventario WHERE nombre LIKE ?"
        self.cargar_datos_tabla(query, (termino,))

    # ==========================================
    # VISTA 2: FORMULARIO DE ALTA / EDICIÓN
    # ==========================================
    def configurar_vista_formulario(self):
        frame_top = ctk.CTkFrame(self.vista_formulario, fg_color="transparent")
        frame_top.pack(fill="x", pady=10, padx=20)
        ctk.CTkButton(frame_top, text="⬅ Volver a la lista", fg_color="gray", command=self.mostrar_lista).pack(side="left")
        
        self.lbl_titulo_form = ctk.CTkLabel(self.vista_formulario, text="Registrar Nuevo Producto", font=("Arial", 24, "bold"))
        self.lbl_titulo_form.pack(pady=(0, 20))

        contenedor_central = ctk.CTkFrame(self.vista_formulario, fg_color="transparent")
        contenedor_central.pack(expand=True)

        form_grid = ctk.CTkFrame(contenedor_central, fg_color="transparent")
        form_grid.pack(pady=10)

        # Fila 1: Nombre
        ctk.CTkLabel(form_grid, text="Nombre del Producto *").grid(row=0, column=0, sticky="w", pady=5)
        self.entry_nombre = ctk.CTkEntry(form_grid, textvariable=self.var_nombre, width=300)
        self.entry_nombre.grid(row=0, column=1, sticky="w", padx=(0, 20), pady=5)
        self.err_nombre = ctk.CTkLabel(form_grid, text="", text_color="red", font=("Arial", 10))
        self.err_nombre.grid(row=1, column=1, sticky="w")

        # Fila 2: Cantidad
        ctk.CTkLabel(form_grid, text="Cantidad a ingresar *").grid(row=2, column=0, sticky="w", pady=5)
        self.entry_cantidad = ctk.CTkEntry(form_grid, textvariable=self.var_cantidad, width=150)
        self.entry_cantidad.grid(row=2, column=1, sticky="w", pady=5)
        self.err_cantidad = ctk.CTkLabel(form_grid, text="", text_color="red", font=("Arial", 10))
        self.err_cantidad.grid(row=3, column=1, sticky="w")

        # Fila 3: Costo Compra
        ctk.CTkLabel(form_grid, text="Costo de Compra ($) *").grid(row=4, column=0, sticky="w", pady=5)
        self.entry_compra = ctk.CTkEntry(form_grid, textvariable=self.var_costo_compra, width=150)
        self.entry_compra.grid(row=4, column=1, sticky="w", pady=5)
        self.err_compra = ctk.CTkLabel(form_grid, text="", text_color="red", font=("Arial", 10))
        self.err_compra.grid(row=5, column=1, sticky="w")

        # Fila 4: Costo Venta al Público
        ctk.CTkLabel(form_grid, text="Precio al Público ($) *").grid(row=6, column=0, sticky="w", pady=5)
        self.entry_venta = ctk.CTkEntry(form_grid, textvariable=self.var_costo_venta, width=150)
        self.entry_venta.grid(row=6, column=1, sticky="w", pady=5)
        self.err_venta = ctk.CTkLabel(form_grid, text="", text_color="red", font=("Arial", 10))
        self.err_venta.grid(row=7, column=1, sticky="w")

        # Botones de Acción
        frame_acciones = ctk.CTkFrame(contenedor_central, fg_color="transparent")
        frame_acciones.pack(pady=(30, 5))

        self.btn_cancelar = ctk.CTkButton(frame_acciones, text="Cancelar", fg_color="gray", hover_color="#555555", command=self.mostrar_lista, height=40, width=150)
        self.btn_cancelar.pack(side="left", padx=10)

        self.btn_guardar = ctk.CTkButton(frame_acciones, text="Guardar Producto", state="disabled", command=self.guardar_producto, height=40, width=150)
        self.btn_guardar.pack(side="left", padx=10)
        
        self.lbl_error_bd = ctk.CTkLabel(contenedor_central, text="", text_color="red", font=("Arial", 12, "bold"))
        self.lbl_error_bd.pack()

    # ==========================================
    # LÓGICA DE VALIDACIÓN Y BASE DE DATOS
    # ==========================================
    def validar_formulario(self, *args):
        es_valido = True
        
        # Validar Nombre
        nombre = self.var_nombre.get()
        if not nombre.strip():
            self.err_nombre.configure(text="El nombre es obligatorio")
            es_valido = False
        else:
            self.err_nombre.configure(text="")

        # Validar Cantidad
        cantidad = self.var_cantidad.get()
        if not cantidad.isdigit() or int(cantidad) < 0:
            self.err_cantidad.configure(text="Debe ser un número entero válido")
            es_valido = False
        else:
            self.err_cantidad.configure(text="")

        # Validar Costo Compra
        try:
            compra = float(self.var_costo_compra.get())
            if compra < 0: raise ValueError
            self.err_compra.configure(text="")
        except ValueError:
            self.err_compra.configure(text="Precio inválido (ej. 15.50)")
            es_valido = False

        # Validar Costo Venta
        try:
            venta = float(self.var_costo_venta.get())
            if venta < 0: raise ValueError
            self.err_venta.configure(text="")
        except ValueError:
            self.err_venta.configure(text="Precio inválido (ej. 25.00)")
            es_valido = False

        # Habilitar o deshabilitar botón Guardar
        if es_valido:
            self.btn_guardar.configure(state="normal")
        else:
            self.btn_guardar.configure(state="disabled")

    def mostrar_lista(self):
        self.vista_formulario.pack_forget()
        self.vista_lista.pack(fill="both", expand=True)
        self.entry_buscar.delete(0, "end") 
        self.cargar_datos_tabla()

    def mostrar_formulario(self, id_prod=None):
        self.vista_lista.pack_forget()
        self.vista_formulario.pack(fill="both", expand=True)
        self.lbl_error_bd.configure(text="") 
        
        if id_prod is None:
            self.lbl_titulo_form.configure(text="Registrar Nuevo Producto")
            self.btn_guardar.configure(text="Guardar Producto")
            
            # Limpiar campos
            self.var_id.set("")
            self.var_nombre.set("")
            self.var_cantidad.set("0")
            self.var_costo_compra.set("0.0")
            self.var_costo_venta.set("0.0")
        else:
            self.lbl_titulo_form.configure(text="Modificar Producto")
            self.btn_guardar.configure(text="Actualizar Producto")
            self.cargar_datos_producto(id_prod)

    def cargar_datos_producto(self, id_prod):
        conn = sqlite3.connect('gimnasio.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM inventario WHERE id=?", (id_prod,))
        fila = cursor.fetchone()
        conn.close()

        if fila:
            self.var_id.set(fila[0])
            self.var_nombre.set(fila[1])
            self.var_cantidad.set(str(fila[2]))
            self.var_costo_compra.set(str(fila[3]))
            self.var_costo_venta.set(str(fila[4]))
            
            self.validar_formulario()

    def guardar_producto(self):
        conn = sqlite3.connect('gimnasio.db')
        cursor = conn.cursor()
        
        id_actual = self.var_id.get()
        nombre = self.var_nombre.get().strip()
        cantidad = int(self.var_cantidad.get())
        compra = float(self.var_costo_compra.get())
        venta = float(self.var_costo_venta.get())

        try:
            if id_actual:
                cursor.execute('''UPDATE inventario SET 
                                nombre=?, cantidad=?, costo_compra=?, costo_venta=?
                                WHERE id=?''', 
                               (nombre, cantidad, compra, venta, id_actual))
                messagebox.showinfo("Éxito", "Producto actualizado correctamente.")
            else:
                cursor.execute('''INSERT INTO inventario 
                                (nombre, cantidad, costo_compra, costo_venta)
                                VALUES (?, ?, ?, ?)''',
                               (nombre, cantidad, compra, venta))
                messagebox.showinfo("Éxito", "Producto registrado correctamente.")
            
            conn.commit()
            self.mostrar_lista()
            
        except Exception as e:
            self.lbl_error_bd.configure(text="Error al guardar en base de datos.")
            print(f"Error técnico: {e}")
        finally:
            conn.close()

    def editar_producto(self, event):
        item_seleccionado = self.tabla.focus()
        if item_seleccionado:
            valores = self.tabla.item(item_seleccionado, "values")
            id_prod = valores[0]
            self.mostrar_formulario(id_prod)