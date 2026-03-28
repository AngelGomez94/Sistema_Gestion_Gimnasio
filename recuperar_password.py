import customtkinter as ctk
import sqlite3
import re

class ForgotPasswordModal(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent) 
        
        self.parent = parent 
        self.title("Recuperar contraseña") 
        
        # Ajustamos un poco el alto para que quepa el texto de las reglas
        ancho, alto = 400, 380 
        x = (self.winfo_screenwidth() // 2) - (ancho // 2)
        y = (self.winfo_screenheight() // 2) - (alto // 2)
        self.geometry(f"{ancho}x{alto}+{x}+{y}")
        
        self.resizable(False, False) 
        self.grab_set() 
        
        # NUEVO: Si el usuario cierra la ventana con la "X" de arriba, ejecutamos nuestra función cerrar_modal
        self.protocol("WM_DELETE_WINDOW", self.cerrar_modal)
        
        # NUEVO: Enlazamos la tecla Enter a esta ventana
        self.bind('<Return>', self.evento_enter)
        
        self.username_var = ctk.StringVar()
        self.new_password_var = ctk.StringVar()
        
        # --- UI: ELEMENTOS VISIBLES INICIALMENTE ---
        self.lbl_title = ctk.CTkLabel(self, text="Recuperar contraseña", font=("Arial", 20, "bold"))
        self.lbl_title.pack(pady=(20, 10))
        
        self.lbl_user = ctk.CTkLabel(self, text="Ingresa tu usuario:")
        self.lbl_user.pack()
        
        self.entry_user = ctk.CTkEntry(self, textvariable=self.username_var, width=200)
        self.entry_user.pack(pady=10)
        
        self.lbl_mensaje = ctk.CTkLabel(self, text="", text_color="red")
        self.lbl_mensaje.pack()
        
        self.frame_botones = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_botones.pack(pady=10)
        
        self.btn_cancelar = ctk.CTkButton(self.frame_botones, text="Cancelar", command=self.cerrar_modal)
        self.btn_cancelar.pack(side="left", padx=10)
        
        self.btn_buscar = ctk.CTkButton(self.frame_botones, text="Buscar usuario", state="disabled", command=self.buscar_usuario)
        self.btn_buscar.pack(side="right", padx=10)
        
        # --- UI: ELEMENTOS OCULTOS PARA CAMBIO DE CONTRASEÑA ---
        self.lbl_new_pass = ctk.CTkLabel(self, text="Introduce el nuevo password:")
        
        # NUEVO: Etiqueta con las reglas de la contraseña (inicia oculta)
        texto_reglas = "Mínimo 8 caracteres, incluye letras, números,\ncaracteres especiales y no números consecutivos."
        self.lbl_reglas_pass = ctk.CTkLabel(self, text=texto_reglas, text_color="gray", font=("Arial", 11))
        
        self.entry_new_pass = ctk.CTkEntry(self, textvariable=self.new_password_var, show="*", width=200)
        self.btn_cambiar = ctk.CTkButton(self, text="Cambiar contraseña", state="disabled", command=self.actualizar_password)
        self.btn_regresar = ctk.CTkButton(self, text="Regresar", command=self.cerrar_modal)

        self.username_var.trace_add("write", self.validar_campo_busqueda)
        self.new_password_var.trace_add("write", self.validar_nuevo_password)

    # NUEVO: Lógica inteligente para la tecla Enter
    def evento_enter(self, event):
        # Si el botón de buscar está visible (mapeado) y habilitado, presionar Enter busca.
        if self.btn_buscar.winfo_ismapped() and self.btn_buscar.cget("state") == "normal":
            self.buscar_usuario()
        # Si el botón de cambiar está visible y habilitado, presionar Enter cambia la contraseña.
        elif self.btn_cambiar.winfo_ismapped() and self.btn_cambiar.cget("state") == "normal":
            self.actualizar_password()

    def validar_campo_busqueda(self, *args):
        if len(self.username_var.get().strip()) > 0:
            self.btn_buscar.configure(state="normal")
        else:
            self.btn_buscar.configure(state="disabled")

    def buscar_usuario(self):
        usuario = self.username_var.get().strip()
        conn = sqlite3.connect('gimnasio.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE username=?", (usuario,))
        resultado = cursor.fetchone()
        conn.close()

        if resultado is None:
            self.lbl_mensaje.configure(text="Usuario no encontrado", text_color="red")
            self.ocultar_campos_password()
        else:
            self.lbl_mensaje.configure(text="")
            self.entry_user.configure(state="disabled") 
            self.btn_buscar.configure(state="disabled")
            
            self.lbl_new_pass.pack(pady=(10, 0))
            # NUEVO: Mostramos la etiqueta de las reglas justo debajo
            self.lbl_reglas_pass.pack(pady=(0, 5)) 
            self.entry_new_pass.pack(pady=5)
            self.btn_cambiar.pack(pady=10)
            
            # NUEVO: Ponemos el cursor automáticamente en el campo de nueva contraseña
            self.entry_new_pass.focus() 

    def ocultar_campos_password(self):
        self.lbl_new_pass.pack_forget()
        self.lbl_reglas_pass.pack_forget() # NUEVO: Ocultamos las reglas si no se necesitan
        self.entry_new_pass.pack_forget()
        self.btn_cambiar.pack_forget()

    def validar_nuevo_password(self, *args):
        pwd = self.new_password_var.get()
        es_valido = True
        
        if len(pwd) < 8: es_valido = False
        if not re.search(r"[a-zA-Z]", pwd): es_valido = False
        if not re.search(r"\d", pwd): es_valido = False
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", pwd): es_valido = False
        
        for i in range(len(pwd) - 2):
            if pwd[i:i+3].isdigit():
                n1, n2, n3 = int(pwd[i]), int(pwd[i+1]), int(pwd[i+2])
                if n2 == n1 + 1 and n3 == n2 + 1:
                    es_valido = False
                    break
                    
        if es_valido:
            self.btn_cambiar.configure(state="normal")
        else:
            self.btn_cambiar.configure(state="disabled")

    def actualizar_password(self):
        usuario = self.username_var.get()
        nuevo_pwd = self.new_password_var.get()
        
        conn = sqlite3.connect('gimnasio.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET password=? WHERE username=?", (nuevo_pwd, usuario))
        conn.commit()
        conn.close()
        
        self.lbl_mensaje.configure(text=f"La contraseña para el usuario {usuario} ha sido actualizada", text_color="green")
        self.ocultar_campos_password()
        self.frame_botones.pack_forget()
        
        self.btn_regresar.pack(pady=20)
        # NUEVO: El foco se va al botón regresar para que si dan Enter, se cierre el modal
        self.btn_regresar.focus()
        self.bind('<Return>', lambda e: self.cerrar_modal())

    def cerrar_modal(self):
        self.parent.limpiar_campos() 
        # NUEVO: Volvemos a mostrar la ventana principal (Login)
        self.parent.deiconify() 
        self.destroy()