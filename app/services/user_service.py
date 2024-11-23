from app.models.models import User
from app.extensions import db
import bcrypt

def get_user_by_username(username):
    return User.query.filter_by(username=username).first()

def signup_user_service(email, username, password):
    """
    Serviço para cadastrar um novo usuário.
    """
    # Verificar se o email ou username já existem
    existing_user = User.query.filter((User.email == email) | (User.username == username)).first()
    if existing_user:
        raise ValueError("Email ou nome de usuário já está em uso.")

    # Criptografar a senha
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Criar um novo usuário
    new_user = User(
        email=email,
        username=username,
        password=hashed_password
    )
    db.session.add(new_user)
    db.session.commit()

    return new_user