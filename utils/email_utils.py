from flask import render_template
from flask_mail import Message

def send_verification_email(email, verification_link):
    """Envia e-mail de verificação para o usuário"""
    from app import mail

    msg = Message(
        subject="Confirme seu e-mail",
        sender="seguenasaga@gmail.com",
        recipients=[email]
    )
    msg.html = render_template("email_verification.html", verification_link=verification_link)
    mail.send(msg)

def send_reset_email(email, reset_link):
    """Envia e-mail com o link de recuperação de senha"""
    from app import mail

    msg = Message(
        subject="Redefinição de Senha - Segue na Saga",
        sender="seguenasaga@gmail.com",
        recipients=[email]
    )
    msg.html = render_template("email_reset_password.html", reset_link=reset_link)
    mail.send(msg)
