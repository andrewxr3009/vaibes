from flask import Blueprint, request, session, jsonify, redirect, url_for, flash, render_template
from app.models.models import User, db
from app.utils.error_handler import handle_error
from app.services.user_service import signup_user_service 
from firebase_admin import auth  # Importando auth do Firebase Admin
import requests
import json
import bcrypt

auth_bp = Blueprint('auth', __name__)

FIREBASE_API_KEY = "AIzaSyCx3huLfApzRJPETN8JwINUnVBoM1Krdvc"  # Substitua pela sua chave

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash("Por favor, preencha todos os campos.", "danger")
            return redirect(url_for('auth.login'))  # Usando o endpoint correto do blueprint 'auth'

        try:
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }

            response = requests.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}",
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                # Verificar se o usuário existe no banco de dados
                user = User.query.filter_by(email=email).first()

                # Se o usuário não existir, criá-lo
                if not user:
                    flash("Usuário não encontrado no banco de dados. Criando um novo usuário.", "warning")
                    user = User(email=email, username=email.split('@')[0])  # Exemplo de nome de usuário
                    db.session.add(user)
                    db.session.commit()

                # Armazenar o ID do usuário na sessão
                session['user_id'] = user.id
                flash("Login bem-sucedido!", "success")
                return redirect(url_for('main.home'))  # Corrigido para 'main.home'
            else:
                flash("Erro ao tentar logar. Verifique suas credenciais.", "danger")
        except Exception as e:
            flash(f"Erro: {str(e)}", "danger")
            return redirect(url_for('auth.login'))  # Usando o endpoint correto 'auth.login'

    return render_template('login.html')


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not email or not username or not password or not confirm_password:
            flash('Todos os campos são obrigatórios', 'danger')
            return redirect(url_for('auth.signup'))

        if password != confirm_password:
            flash('As senhas não coincidem', 'danger')
            return redirect(url_for('auth.signup'))

        try:
            # Criação do usuário no Firebase
            firebase_user = auth.create_user(
                email=email,
                password=password,
                display_name=username
            )

            firebase_id = firebase_user.uid  # Pega o ID gerado pelo Firebase

            # Criar novo usuário no banco de dados local
            new_user = User(
                firebase_id=firebase_id,  # Preenche o campo 'firebase_id'
                username=username,
                email=email,
                password=bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
                bio='{}',  # Passando um array vazio para o campo bio
                interests='{}',  # Passando um array vazio para o campo interests
                profile_picture=None
            )

            db.session.add(new_user)
            db.session.commit()

            flash('Usuário criado com sucesso!', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            flash(f"Erro ao criar usuário: {str(e)}", 'danger')
            return redirect(url_for('auth.signup'))

    return render_template('signup.html')
