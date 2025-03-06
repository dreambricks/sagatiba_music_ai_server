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

def send_reset_email(email, reset_link):
    """Envia e-mail com o link de recuperação de senha"""
    from app import mail

    msg = Message(
        subject="Redefinição de Senha - Segue na Saga",
        sender="no-reply@seguenasaga.sagatiba.com",
        recipients=[email]
    )
    msg.body = f"Para redefinir sua senha, clique no link: {reset_link}"
    msg.html = f"""
        <p>Olá,</p>
        <p>Para redefinir sua senha, clique no link abaixo:</p>
        <p><a href="{reset_link}">Redefinir Senha</a></p>
        <p>Se você não solicitou esta alteração, ignore esta mensagem.</p>
    """
    mail.send(msg)