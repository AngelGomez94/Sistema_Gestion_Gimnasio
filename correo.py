import smtplib
from email.mime.text import MIMEText

def prueba_rapida():
    remitente = "notificacionessportlife@gmail.com"
    password = "klcccpcccuzwkyue" # Sin espacios
    destinatario = "angel140994@gmail.com"

    try:
        print("Conectando con Google...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remitente, password)
        
        msg = MIMEText("Si lees esto, el ERP ya puede mandar correos.")
        msg['Subject'] = "Prueba de Conexión ERP"
        
        server.sendmail(remitente, destinatario, msg.as_string())
        server.quit()
        print("¡Éxito! El correo ha sido enviado.")
    except Exception as e:
        print(f"Error en la prueba: {e}")

prueba_rapida()