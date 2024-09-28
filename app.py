from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid
import os
import requests
import io
import firebase_admin
from firebase_admin import credentials, auth, firestore
import bcrypt
from google.cloud import storage
import json

# Inicializar o Firebase Admin SDK
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'storageBucket': 'app-vaibes.appspot.com'  # Substitua pelo seu bucket do Firebase Storage
})

# Configurações do Firebase Storage
storage_client = storage.Client.from_service_account_json("serviceAccountKey.json")
bucket_name = "app-vaibes.appspot.com"  # Substitua pelo nome do seu bucket do Firebase Storage
bucket = storage_client.bucket(bucket_name)

# Inicialização do Flask
app = Flask(__name__)
app.secret_key = 'a3n0d0r4e0w9'  # Substitua por uma chave secreta adequada
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres.txyhqnbmlpcywyapxypm:5edqw3n4lhxCacLm@aws-0-us-west-1.pooler.supabase.com:6543/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuração de upload de arquivos
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')  # Caminho correto para a pasta uploads
app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png'}

# Instância do SQLAlchemy
db = SQLAlchemy(app)

# Funções auxiliares
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def save_profile_picture(picture):
    if picture and allowed_file(picture.filename):
        ext = picture.filename.rsplit('.', 1)[1].lower()
        new_filename = f"{uuid.uuid4().hex}.{ext}"
        file_stream = io.BytesIO(picture.read())

        try:
            # Suba o arquivo para o Firebase Storage
            blob = bucket.blob(new_filename)
            blob.upload_from_file(file_stream, content_type=picture.content_type)
            blob.make_public()  # Opcional: tornar a imagem pública
            return blob.public_url
        except Exception as e:
            print(f"Erro ao salvar imagem: {e}")
            return None
    return None

# Modelos do banco de dados
class Follower(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', foreign_keys=[user_id], back_populates='following')
    follower = db.relationship('User', foreign_keys=[follower_id], back_populates='followers')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firebase_id = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    bio = db.Column(db.String(255))
    profile_picture = db.Column(db.String(255))
    posts = db.relationship('Post', back_populates='author', lazy=True)
    likes = db.relationship('Like', back_populates='user', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', back_populates='user', lazy=True, cascade="all, delete-orphan")
    following = db.relationship('Follower', foreign_keys='Follower.user_id', back_populates='user', lazy='dynamic')
    shares = db.relationship('Share', back_populates='sharer', lazy=True)
    followers = db.relationship('Follower', foreign_keys='Follower.follower_id', back_populates='follower', lazy='dynamic')

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    likes = db.relationship('Like', back_populates='post', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', back_populates='post', lazy=True, cascade="all, delete-orphan")
    shares = db.relationship('Share', back_populates='shared_post', lazy=True)
    author = db.relationship('User', back_populates='posts')

class Share(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    shared_post = db.relationship('Post', back_populates='shares')
    sharer = db.relationship('User', back_populates='shares', foreign_keys=[user_id])

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    post = db.relationship('Post', back_populates='likes')
    user = db.relationship('User', back_populates='likes')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    post = db.relationship('Post', back_populates='comments')
    user = db.relationship('User', back_populates='comments')

# Cria os bancos de dados
def create_tables():
    with app.app_context():
        db.create_all()

create_tables()

def update_last_login(user_id):
    db_fs = firestore.client()
    
    # Data e hora atuais
    last_login_time = datetime.now()
    
    # Atualizando o campo 'last_login' no Firestore (coleção 'users')
    try:
        db_fs.collection('users').document(user_id).update({
            'last_login': last_login_time
        })
    except Exception as e:
        print(f"Erro ao atualizar último login: {e}")

def get_user_by_username(username):
    return User.query.filter_by(username=username).first()

def like_post_action(post_id, user):
    post = Post.query.get(post_id)
    if post:
        existing_like = Like.query.filter_by(post_id=post_id, user_id=user.id).first()
        if existing_like:
            return {'status': 'error', 'message': 'Você já curtiu este post.'}

        new_like = Like(post_id=post.id, user_id=user.id)
        db.session.add(new_like)
        db.session.commit()
        
        # Atualiza a contagem de curtidas
        like_count = Like.query.filter_by(post_id=post_id).count()
        return {'status': 'success', 'like_count': like_count}
    
    return {'status': 'error', 'message': 'Post não encontrado.'}

def comment_post_action(post_id, user, content):
    post = Post.query.get(post_id)
    if post and content:
        new_comment = Comment(post_id=post.id, user_id=user.id, content=content)
        db.session.add(new_comment)
        db.session.commit()
        
        comments = Comment.query.filter_by(post_id=post_id).all()
        comments_data = [{'username': c.user.username, 'content': c.content} for c in comments]
        return {'status': 'success', 'message': 'Comentário adicionado!', 'comments': comments_data}
    
    return {'status': 'error', 'message': 'Erro ao adicionar comentário.'}

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Se o usuário estiver autenticado, busque as informações necessárias
    user = User.query.get(session.get('user_id'))
    
    if user is None:
        flash('Usuário não encontrado.')
        return redirect(url_for('logout'))

    user_id = user.id
    posts = Post.query.order_by(Post.timestamp.asc()).all()
    for post in posts:
        post.comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.timestamp.asc()).all()

    recent_users = User.query.order_by(User.id.desc()).limit(5).all()
    
    user_agent = request.headers.get('User-Agent')
    
    # Verifica o User-Agent para renderizar o template correto
    if 'Mobile' in user_agent:
        return render_template('ios_home.html', posts=posts, recent_users=recent_users, user=user)
    else:
        return render_template('home.html', posts=posts, recent_users=recent_users, user=user)

@app.route('/profile/<username>')
def profile(username):
    user = get_user_by_username(username)
    if user is None:
        flash('Usuário não encontrado.')
        return redirect(url_for('home'))

    posts = Post.query.filter_by(user_id=user.id).order_by(Post.timestamp.desc()).all()
    return render_template('profile.html', user=user, posts=posts)

@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        # Captura os dados do formulário
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Debug: imprimir dados recebidos
        print(f"Email: {email}, Username: {username}, Password: {password}, Confirm Password: {confirm_password}")

        # Verifica se todos os campos necessários foram preenchidos
        if not email or not username or not password or not confirm_password:
            flash('Todos os campos são obrigatórios', 'danger')
            return redirect(url_for('signup'))
        
        # Verifica se as senhas coincidem
        if password != confirm_password:
            flash('As senhas não coincidem', 'danger')
            return redirect(url_for('signup'))

        # Verificar se já existe um usuário com esse email ou username
        existing_user = User.query.filter((User.email == email) | (User.username == username)).first()
        if existing_user:
            flash('Email ou nome de usuário já existe.', 'danger')
            return redirect(url_for('signup'))

        try:
            # Cria um novo usuário no Firebase
            firebase_user = auth.create_user(
                email=email,
                password=password,
                display_name=username
            )
            # Captura o firebase_id
            firebase_id = firebase_user.uid

            # Salvar imagem de perfil no Firebase Storage
            picture = request.files.get('profile_picture')
            profile_picture_url = save_profile_picture(picture) if picture else None

            # Criptografa a senha antes de armazená-la no banco de dados
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Criar um novo usuário na base de dados
            new_user = User(
                firebase_id=firebase_id,
                username=username,
                email=email,
                password=hashed_password,
                profile_picture=profile_picture_url
            )
            db.session.add(new_user)
            db.session.commit()

            # Criar documento no Firestore para o usuário
            db_fs = firestore.client()
            db_fs.collection('users').document(firebase_id).set({
                'email': email,
                'username': username,
                'bio': '',
                'profile_picture': profile_picture_url,
                'last_login': datetime.now()
            })

            flash('Usuário criado com sucesso! Faça o login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            # Adiciona um log de erro se a criação do usuário falhar
            print(f"Erro ao criar usuário: {e}")
            flash('Erro ao criar usuário. Tente novamente.', 'danger')
            return redirect(url_for('signup'))

    return render_template('signup.html')  # Retorna o formulário de cadastro se for um GET

@app.route('/post', methods=['GET', 'POST'])
def create_post():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        content = request.form['content']
        if content:
            new_post = Post(content=content, user_id=user.id)
            db.session.add(new_post)
            db.session.commit()
            flash('Post criado com sucesso!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Conteúdo do post não pode estar vazio.', 'danger')

    return render_template('create_post.html', user=user)

# Adicione essa rota para ver os posts de um usuário
@app.route('/user/<username>/posts')
def user_posts(username):
    user = get_user_by_username(username)
    if user is None:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('home'))

    posts = Post.query.filter_by(user_id=user.id).order_by(Post.timestamp.desc()).all()
    return render_template('user_posts.html', user=user, posts=posts)

# Defina sua API Key do Firebase
FIREBASE_API_KEY = "AIzaSyCx3huLfApzRJPETN8JwINUnVBoM1Krdvc"  # Substitua com a sua API Key do Firebase

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash("Por favor, preencha todos os campos.", "danger")
            return redirect(url_for('login'))

        try:
            # Fazer a chamada à API REST do Firebase para autenticação
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
                data = response.json()
                id_token = data['idToken']
                local_id = data['localId']

                # Verificar o usuário no banco de dados
                user = User.query.filter_by(email=email).first()
                if not user:
                    flash("Usuário não encontrado no banco de dados.", "danger")
                    return redirect(url_for('login'))

                # Set session
                session['user_id'] = user.id
                session['firebase_id'] = local_id

                flash("Login bem-sucedido!", "success")

                # Atualizar último login no Firebase
                update_last_login(local_id)

                # Redirecionar para a página inicial
                return redirect(url_for('home'))
            else:
                data = response.json()
                error_message = data.get('error', {}).get('message', 'Erro desconhecido.')
                flash(f"Erro ao tentar logar: {error_message}", "danger")
                return redirect(url_for('login'))

        except Exception as e:
            flash(f"Erro ao tentar logar: {str(e)}", "danger")
            return redirect(url_for('login'))

    # Método GET: renderiza o formulário de login
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('firebase_id', None)
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('login'))

@app.route('/upload_profile_picture', methods=['POST'])
def upload_profile_picture():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        picture = request.files.get('profile_picture')
        if picture:
            filename = save_profile_picture(picture)
            if filename:
                user.profile_picture = filename
                db.session.commit()
                flash('Imagem de perfil atualizada com sucesso!', 'success')
            else:
                flash('Erro ao fazer upload da imagem.', 'danger')
        else:
            flash('Nenhuma imagem foi enviada.', 'warning')
    
    return redirect(url_for('profile', username=user.username))

@app.route('/like_post/<int:post_id>', methods=['POST'])
def like_post(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    result = like_post_action(post_id, user)

    return jsonify(result)

@app.route('/comment_post/<int:post_id>', methods=['POST'])
def comment_post(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    content = request.form.get('content')
    result = comment_post_action(post_id, user, content)

    return jsonify(result)

@app.route('/share_post/<int:post_id>', methods=['POST'])
def share_post(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    post = Post.query.get(post_id)

    if post:
        new_share = Share(post_id=post.id, user_id=user.id)
        db.session.add(new_share)
        db.session.commit()
        flash('Post compartilhado com sucesso!', 'success')
    else:
        flash('Post não encontrado.', 'danger')

    return redirect(url_for('home'))

@app.route('/user/<username>/followers')
def manage_followers(username):
    user = get_user_by_username(username)
    if user is None:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('home'))

    followers_list = Follower.query.filter_by(user_id=user.id).all()
    follower_usernames = [User.query.get(f.follower_id).username for f in followers_list]

    return render_template('followers.html', user=user, followers=follower_usernames)

@app.route('/user/<username>/following')
def following(username):
    user = get_user_by_username(username)
    if user is None:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('home'))

    following_list = Follower.query.filter_by(follower_id=user.id).all()
    following_usernames = [User.query.get(f.user_id).username for f in following_list]

    return render_template('following.html', user=user, following=following_usernames)

@app.route('/follow_user/<username>', methods=['POST'])
def follow_user(username):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_to_follow = get_user_by_username(username)
    user = User.query.get(session['user_id'])

    if user_to_follow and user_to_follow.id != user.id:
        existing_follow = Follower.query.filter_by(user_id=user_to_follow.id, follower_id=user.id).first()
        if existing_follow:
            flash('Você já está seguindo este usuário.', 'warning')
        else:
            new_follow = Follower(user_id=user_to_follow.id, follower_id=user.id)
            db.session.add(new_follow)
            db.session.commit()
            flash('Você começou a seguir este usuário!', 'success')
    else:
        flash('Erro ao seguir o usuário.', 'danger')

    return redirect(url_for('profile', username=username))

@app.route('/unfollow_user/<username>', methods=['POST'])
def unfollow_user(username):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_to_unfollow = get_user_by_username(username)
    user = User.query.get(session['user_id'])

    if user_to_unfollow:
        existing_follow = Follower.query.filter_by(user_id=user_to_unfollow.id, follower_id=user.id).first()
        if existing_follow:
            db.session.delete(existing_follow)
            db.session.commit()
            flash('Você deixou de seguir este usuário.', 'success')
        else:
            flash('Você não está seguindo este usuário.', 'warning')
    else:
        flash('Erro ao deixar de seguir o usuário.', 'danger')

    return redirect(url_for('profile', username=username))

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    if query:
        users = User.query.filter(User.username.ilike(f'%{query}%')).all()
        posts = Post.query.filter(Post.content.ilike(f'%{query}%')).all()
        return render_template('search_results.html', users=users, posts=posts)
    flash('Por favor, insira um termo de pesquisa válido.', 'warning')
    return redirect(url_for('home'))

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    # Verifica se o usuário está autenticado
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Busca o post pelo ID
    post = Post.query.get(post_id)
    if post is None:
        flash('Post não encontrado.', 'danger')
        return redirect(url_for('home'))

    # Busca os comentários do post
    comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.timestamp.asc()).all()

    # Renderiza o template com os detalhes do post e comentários
    return render_template('post_detail.html', post=post, comments=comments)


# Inicialização da aplicação
if __name__ == '__main__':
    app.run(debug=True)
