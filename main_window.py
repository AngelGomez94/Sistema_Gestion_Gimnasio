import customtkinter as ctk
from modulo_miembros import MiembrosFrame # Importamos el módulo de miembros

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Sistema de Gestión de Gimnasio - Dashboard")
        
        # 1. Definimos un tamaño base seguro y lo centramos EXACTAMENTE primero
        ancho_pantalla = self.winfo_screenwidth()
        alto_pantalla = self.winfo_screenheight()
        ancho_base = 1024
        alto_base = 768
        
        x = (ancho_pantalla // 2) - (ancho_base // 2)
        y = (alto_pantalla // 2) - (alto_base // 2)
        
        # Asignamos la geometría base centrada
        self.geometry(f"{ancho_base}x{alto_base}+{x}+{y}")
        self.minsize(800, 600) 
        
        self.grid_rowconfigure(0, weight=1) 
        self.grid_columnconfigure(1, weight=1) 
        
        # --- MENÚ LATERAL (SIDEBAR) ---
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew") 
        self.sidebar.pack_propagate(False) 
        
        self.sidebar_expanded = True 
        
        self.btn_toggle = ctk.CTkButton(self.sidebar, text="☰   Cerrar Menú", anchor="w", width=200, command=self.toggle_sidebar)
        self.btn_toggle.pack(pady=(20, 20), padx=10, fill="x")
        
        self.lista_modulos = [
            "🏠   Inicio", 
            "✅   Recepción", 
            "👥   Miembros", 
            "💰   Pagos",
            "🎁   Promociones", 
            "🛒   Punto de Venta", 
            "📦   Inventario",
            "📊   Reportes", 
            "⚙️   Configuración"
        ]
        
        self.botones_menu = [] 
        
        # CICLO ÚNICO PARA CREAR LOS BOTONES DEL MENÚ
        for mod in self.lista_modulos:
            btn = ctk.CTkButton(
                self.sidebar, 
                text=mod, 
                anchor="w", 
                width=200,
                fg_color="transparent", 
                text_color=("gray10", "gray90"), 
                hover_color=("gray70", "gray30"),
                height=40,
                command=lambda m=mod: self.abrir_modulo(m) # Acción al hacer clic
            )
            btn.pack(pady=2, padx=10, fill="x")
            self.botones_menu.append((btn, mod)) 
            
        # BOTÓN DE CERRAR SESIÓN (Hasta abajo)
        self.btn_logout = ctk.CTkButton(
            self.sidebar, 
            text="🚪   Cerrar Sesión", 
            anchor="w", 
            width=200, 
            fg_color="transparent", 
            text_color="#ff6666", 
            hover_color=("gray70", "gray30"),
            height=40,
            command=self.cerrar_sesion
        )
        self.btn_logout.pack(side="bottom", pady=20, padx=10, fill="x")

        # --- ÁREA PRINCIPAL (DASHBOARD) ---
        self.main_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        self.lbl_welcome = ctk.CTkLabel(self.main_frame, text="Bienvenido a SportLife GYM", font=("Arial", 28, "bold"), text_color="gray50")
        self.lbl_welcome.pack(expand=True) 

        # 2. Le decimos al sistema que espere 50 milisegundos y luego intente maximizar
        self.after(50, self.maximizar_ventana)

    # --- FUNCIONES DE LA VENTANA ---
    def abrir_modulo(self, nombre_modulo):
        # Limpiamos el main_frame (destruimos lo que haya adentro)
        for widget in self.main_frame.winfo_children():
            widget.destroy()
            
        # Verificamos qué botón se presionó
        if "Miembros" in nombre_modulo:
            vista = MiembrosFrame(self.main_frame)
            vista.pack(fill="both", expand=True)
        else:
            lbl = ctk.CTkLabel(self.main_frame, text=f"Módulo: {nombre_modulo}\n(En construcción)", font=("Arial", 24))
            lbl.pack(expand=True)

    def maximizar_ventana(self):
        try:
            self.state('zoomed')
        except:
            pass 

    def toggle_sidebar(self):
        if self.sidebar_expanded:
            self.sidebar.configure(width=60)
            self.btn_toggle.configure(text="☰", width=40) 
            
            for btn, texto_completo in self.botones_menu:
                emoji = texto_completo.split("   ")[0] 
                btn.configure(text=emoji, width=40)
                
            self.btn_logout.configure(text="🚪", width=40)
            self.sidebar_expanded = False
        else:
            self.sidebar.configure(width=220)
            self.btn_toggle.configure(text="☰   Cerrar Menú", width=200)
            
            for btn, texto_completo in self.botones_menu:
                btn.configure(text=texto_completo, width=200)
                
            self.btn_logout.configure(text="🚪   Cerrar Sesión", width=200)
            self.sidebar_expanded = True

    def cerrar_sesion(self):
        self.destroy() 
        from login import LoginApp 
        app_login = LoginApp()
        app_login.mainloop()

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()