import customtkinter as ctk
import sqlite3
from recuperar_password import ForgotPasswordModal
from main_window import MainWindow

class LoginApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        ctk.set_appearance_mode("System")  
        ctk.set_default_color_theme("blue") 
        
        self.title("Sistema de TeamSportLife de Gimnasio - Login")
        
        ancho, alto = 400, 350
        x = (self.winfo_screenwidth() // 2) - (ancho // 2)
        y = (self.winfo_screenheight() // 2) - (alto // 2)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.resizable(False, False) 
        
        self.username_var = ctk.StringVar()
        self.password_var = ctk.StringVar()
        
        self.username_var.trace_add("write", self.validar_campos_login)
        self.password_var.trace_add("write", self.validar_campos_login)

        self.crear_widgets()
        
        # NUEVO: Enlazamos la tecla 'Enter' (Return) a una función de la ventana
        self.bind('<Return>', self.evento_enter)

    def crear_widgets(self):
        lbl_titulo = ctk.CTkLabel(self, text="Bienvenido", font=("Arial", 24, "bold"))
        lbl_titulo.pack(pady=(30, 20))
        
        self.entry_user = ctk.CTkEntry(self, placeholder_text="Usuario", textvariable=self.username_var, width=250)
        self.entry_user.pack(pady=10)
        
        self.entry_pass = ctk.CTkEntry(self, placeholder_text="Contraseña", textvariable=self.password_var, show="*", width=250)
        self.entry_pass.pack(pady=10)
        
        self.lbl_error = ctk.CTkLabel(self, text="", text_color="red")
        self.lbl_error.pack()
        
        self.btn_login = ctk.CTkButton(self, text="Iniciar sesión", state="disabled", command=self.iniciar_sesion)
        self.btn_login.pack(pady=(10, 5))
        
        self.btn_forgot = ctk.CTkButton(self, text="¿Olvidaste tu contraseña?", fg_color="transparent", text_color="gray", hover_color="#333333", command=self.abrir_modal_recuperar)
        self.btn_forgot.pack(pady=5)

    def validar_campos_login(self, *args):
        user = self.username_var.get().strip()
        pwd = self.password_var.get()
        
        if len(user) > 0 and len(pwd) >= 3:
            self.btn_login.configure(state="normal")
        else:
            self.btn_login.configure(state="disabled")

    # NUEVO: Función que se ejecuta al presionar Enter
    def evento_enter(self, event):
        # Solo intenta hacer login si el botón está habilitado (reglas cumplidas)
        if self.btn_login.cget("state") == "normal":
            self.iniciar_sesion()

    def iniciar_sesion(self):
        usuario = self.username_var.get().strip()
        password = self.password_var.get()
        
        conn = sqlite3.connect('gimnasio.db')
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM usuarios WHERE username=?", (usuario,))
        resultado = cursor.fetchone()
        conn.close()

        if resultado is None:
            self.lbl_error.configure(text="El usuario no existe", text_color="red")
        else:
            bd_password = resultado[0]
            if password == bd_password:
                # NUEVO: Login exitoso, abrimos el sistema
                self.destroy() # Destruimos la ventana de login por completo
                app_principal = MainWindow() # Instanciamos el cascarón
                app_principal.mainloop() # Arrancamos el loop de la ventana principal
            else:
                self.lbl_error.configure(text="Password incorrecto", text_color="red")

    def abrir_modal_recuperar(self):
        self.limpiar_campos()
        self.lbl_error.configure(text="")
        
        # NUEVO: Ocultamos la ventana de Login actual antes de abrir el modal
        self.withdraw() 
        
        ForgotPasswordModal(self) 

    def limpiar_campos(self):
        self.username_var.set("")
        self.password_var.set("")