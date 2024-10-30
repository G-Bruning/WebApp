import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

def send(destinatario, nova_senha):
    remetente = "gbruning293@gmail.com"
    assunto = "Sua Nova Senha"
    corpo = f"""
    Prezado usuário,

    Caso você tenha perdido a sua senha de acesso, sua nova senha é: {nova_senha}

    Por favor, faça login com esta senha e altere-a imediatamente por motivos de segurança.
    """
    
    senha = "nfbv qwsm bfuz accl"
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()

    try:
        server.login(remetente, senha)
        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = destinatario
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo, 'plain'))

        server.sendmail(remetente, destinatario, msg.as_string())
        print("Email enviado com sucesso!")

    except Exception as e:
        print(f"Falha ao enviar email: {e}")

    finally:
        server.quit()
