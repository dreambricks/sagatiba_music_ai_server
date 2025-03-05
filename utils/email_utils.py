from flask_mail import Message

def send_verification_email(email, verification_link):
    """Envia e-mail de verificação para o usuário"""
    from app import mail

    msg = Message(
        subject="Confirme seu e-mail",
        sender="no-reply@seusite.com",
        recipients=[email]
    )
    msg.body = f"Por favor, clique no link para confirmar seu e-mail: {verification_link}"
    msg.html = f"""
        <p>Olá,</p>
        <p>Para ativar sua conta, clique no link abaixo:</p>
        <p><a href="{verification_link}">Confirmar e-mail</a></p>
        <p>Se você não solicitou este cadastro, ignore esta mensagem.</p>
    """
    mail.send(msg)
