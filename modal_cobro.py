import customtkinter as ctk

class ModalCobro(ctk.CTkToplevel):
    def __init__(self, parent, monto_plan, monto_locker, monto_inscripcion, callback_exito):
        # Nota: 'parent' aquí debe ser la ventana principal (MainWindow)
        super().__init__(parent)
        
        self.monto_plan = float(monto_plan)
        self.monto_locker = float(monto_locker)
        self.monto_inscripcion = float(monto_inscripcion)
        
        # El total ahora incluye la inscripción
        self.monto_total = self.monto_plan + self.monto_locker + self.monto_inscripcion
        self.callback_exito = callback_exito
        
        self.title("Punto de Cobro")
        
        # --- LÓGICA DE CENTRADO DINÁMICO ---
        anchura_modal = 400
        altura_modal = 500
        self.master.update_idletasks()
        ventana_principal = self.master.winfo_toplevel()
        anchura_padre = ventana_principal.winfo_width()
        altura_padre = ventana_principal.winfo_height()
        pos_x_padre = ventana_principal.winfo_rootx()
        pos_y_padre = ventana_principal.winfo_rooty()
        
        coordenada_x = pos_x_padre + (anchura_padre // 2) - (anchura_modal // 2)
        coordenada_y = pos_y_padre + (altura_padre // 2) - (altura_modal // 2) - 20
        self.geometry(f"{anchura_modal}x{altura_modal}+{coordenada_x}+{coordenada_y}")
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set() 
        self.focus_force()
        self.protocol("WM_DELETE_WINDOW", self.cancelar)
        
        self.var_metodo = ctk.StringVar(value="Efectivo")
        self.var_recibido = ctk.StringVar()
        self.var_recibido.trace_add("write", self.calcular_cambio)
        
        # --- UI DESGLOSE ---
        ctk.CTkLabel(self, text="Resumen de Cobro", font=("Arial", 20, "bold")).pack(pady=(20, 10))
        
        ctk.CTkLabel(self, text=f"Membresía/Mant: ${self.monto_plan:,.2f}", font=("Arial", 14)).pack()
        
        # NUEVO: DIBUJAMOS EL RENGLÓN DE INSCRIPCIÓN SI EXISTE
        if self.monto_inscripcion > 0:
            ctk.CTkLabel(self, text=f"Inscripción: ${self.monto_inscripcion:,.2f}", font=("Arial", 14)).pack()
            
        if self.monto_locker > 0:
            ctk.CTkLabel(self, text=f"Renta de Locker: ${self.monto_locker:,.2f}", font=("Arial", 14)).pack()
            
        ctk.CTkLabel(self, text=f"Total a Pagar: ${self.monto_total:,.2f}", font=("Arial", 28, "bold"), text_color="#2ecc71").pack(pady=15)
        
        # --- MÉTODO DE PAGO ---
        ctk.CTkLabel(self, text="Método de Pago:").pack()
        self.combo_metodo = ctk.CTkComboBox(self, values=["Efectivo", "Tarjeta"], variable=self.var_metodo, command=self.cambiar_metodo)
        self.combo_metodo.pack(pady=5)
        
        self.frame_dinamico = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_dinamico.pack(fill="x", padx=40, pady=10)
        
        self.lbl_recibido = ctk.CTkLabel(self.frame_dinamico, text="Monto Recibido ($):")
        self.entry_recibido = ctk.CTkEntry(self.frame_dinamico, textvariable=self.var_recibido, justify="center", font=("Arial", 16))
        self.lbl_cambio = ctk.CTkLabel(self.frame_dinamico, text="Cambio: $0.00", font=("Arial", 18, "bold"), text_color="#f1c40f")
        
        self.lbl_aviso = ctk.CTkLabel(self.frame_dinamico, text="⚠️ Pase la tarjeta por la terminal.\nSolo continúe si el cobro fue EXITOSO.", text_color="#e74c3c", font=("Arial", 14, "bold"))
        
        frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        frame_botones.pack(pady=20)
        
        self.btn_cancelar = ctk.CTkButton(frame_botones, text="Cancelar", fg_color="gray", hover_color="#555555", command=self.cancelar, width=120)
        self.btn_cancelar.pack(side="left", padx=10)
        
        self.btn_cobrar = ctk.CTkButton(frame_botones, text="Cobrar e Imprimir", command=self.procesar_pago, width=150, state="disabled")
        self.btn_cobrar.pack(side="left", padx=10)
        
        self.cambiar_metodo("Efectivo")

    def cancelar(self):
        self.grab_release()
        self.destroy()

    def cambiar_metodo(self, metodo):
        for widget in self.frame_dinamico.winfo_children():
            widget.pack_forget()
            
        if metodo == "Efectivo":
            self.lbl_recibido.pack(pady=5)
            self.entry_recibido.pack(pady=5)
            self.lbl_cambio.pack(pady=10)
            self.entry_recibido.focus()
            self.calcular_cambio()
        else:
            self.lbl_aviso.pack(pady=20)
            self.btn_cobrar.configure(state="normal")

    def calcular_cambio(self, *args):
        if self.var_metodo.get() != "Efectivo": return
        texto_recibido = self.var_recibido.get()
        try:
            recibido = float(texto_recibido) if texto_recibido.strip() != "" else 0.0
            cambio = recibido - self.monto_total
            if cambio >= 0:
                self.lbl_cambio.configure(text=f"Cambio: ${cambio:,.2f}", text_color="#2ecc71")
                self.btn_cobrar.configure(state="normal")
            else:
                self.lbl_cambio.configure(text=f"Faltan: ${abs(cambio):,.2f}", text_color="#e74c3c")
                self.btn_cobrar.configure(state="disabled")
        except ValueError:
            self.lbl_cambio.configure(text="Ingrese solo números", text_color="#e74c3c")
            self.btn_cobrar.configure(state="disabled")

    def procesar_pago(self):
        metodo = self.var_metodo.get()
        recibido = self.var_recibido.get() if metodo == "Efectivo" else str(self.monto_total)
        self.grab_release()
        self.destroy()
        # Mandamos todo de regreso a modulo_miembros
        self.callback_exito(metodo, recibido, self.monto_plan, self.monto_locker)