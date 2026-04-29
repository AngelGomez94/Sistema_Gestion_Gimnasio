from database import setup_db # Importamos la función desde database.py
from login import LoginApp # Importamos la clase principal desde login.py

if __name__ == "__main__":
    # 1. Aseguramos que la BD exista y tenga el usuario administrador
    setup_db() 
    
    # 2. Instanciamos la clase del Login y arrancamos el programa
    app = LoginApp() 
    app.mainloop()
    #Nuevo comentario
    