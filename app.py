from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid
import os
import requests
from supabase import create_client, Client
import io
import firebase_admin
from firebase_admin import credentials, auth
import bcrypt


# Inicializar o Firebase Admin SDK
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

# Configurações do Supabase
url = 'https://txyhqnbmlpcywyapxypm.supabase.co'
key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR4eWhxbmJtbHBjeXd5YXB4eXBtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjU4MTczMjYsImV4cCI6MjA0MTM5MzMyNn0.vAwDYGlUQ0KlrEkMooHmyxVL88SwkVJKBzghiNzoWJo'
supabase: Client = create_client(url, key)

app = Flask(__name__)
app.secret_key = 'a3n0d0r4e0w9'  # Substitua por uma chave secreta adequada
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres.txyhqnbmlpcywyapxypm:5edqw3n4lhxCacLm@aws-0-us-west-1.pooler.supabase.com:6543/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuração de upload de arquivos
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')  # Caminho correto para a pasta uploads
app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png'}

# Instância do SQLAlchemy
db = SQLAlchemy(app)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def save_profile_picture(picture):
    if picture and allowed_file(picture.filename):
        ext = picture.filename.rsplit('.', 1)[1].lower()
        new_filename = f"{uuid.uuid4().hex}.{ext}"
        file_stream = io.BytesIO(picture.read())
        
        try:
            # Suba o arquivo para o Supabase Storage
            response = supabase.storage().from_("vaibes-cloud").upload(new_filename, file_stream)
            
            if response.status_code == 200:
                return new_filename
            else:
                # Log de erro detalhado
                print(f"Erro ao fazer upload para o Supabase: {response.text}")
                return None
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
    profile_picture = db.Column(db.String(120))
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
    if 'firebase_user' not in session:
        return redirect(url_for('login'))
    
    # Se o usuário estiver autenticado, busque as informações necessárias
    user = User.query.filter_by(email=session.get('username')).first()  # Ou use 'firebase_user' para buscar o id do Firebase
    
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

from flask import request, jsonify, render_template
from firebase_admin import auth  # Certifique-se de que você tenha a biblioteca do Firebase Admin instalada
import bcrypt

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
            return jsonify({'message': 'Todos os campos são obrigatórios'}), 400
        
        # Verifica se as senhas coincidem
        if password != confirm_password:
            return jsonify({'message': 'As senhas não coincidem'}), 400

        try:
            # Cria um novo usuário no Firebase
            firebase_user = auth.create_user(
                email=email,
                password=password,
            )
            # Captura o firebase_id
            firebase_id = firebase_user.uid

            # Criptografa a senha antes de armazená-la no banco de dados
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            # Cria um novo usuário na sua base de dados
            new_user = User(firebase_id=firebase_id, username=username, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()

            return jsonify({'message': 'Usuário criado com sucesso'}), 201
        except Exception as e:
            # Adiciona um log de erro se a criação do usuário falhar
            print(f"Erro ao criar usuário: {e}")
            return jsonify({'message': 'Erro ao criar usuário. Tente novamente.'}), 400

    return render_template('signup.html')  # Retorna o formulário de cadastro se for um GET

@app.route('/post', methods=['GET', 'POST'])
def create_post():
    if 'firebase_user' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['firebase_user'])

    if request.method == 'POST':
        content = request.form['content']
        if content:
            new_post = Post(content=content, user_id=user.id)
            db.session.add(new_post)
            db.session.commit()
            flash('Post criado com sucesso!')
            return redirect(url_for('home'))
        else:
            flash('Conteúdo do post não pode estar vazio.')

    return render_template('create_post.html', user=user)

# Adicione essa rota para ver os posts de um usuário
@app.route('/user/<username>/posts')
def user_posts(username):
    user = get_user_by_username(username)
    if user is None:
        flash('Usuário não encontrado.')
        return redirect(url_for('home'))

    posts = Post.query.filter_by(user_id=user.id).order_by(Post.timestamp.desc()).all()
    return render_template('user_posts.html', user=user, posts=posts)



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['username'] = user.email
            session['firebase_user'] = user.id  # Armazena o id do Firebase

            flash('Login realizado com sucesso!')
            return redirect(url_for('home'))
        else:
            flash('Email ou senha incorretos.')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('firebase_user', None)
    flash('Logout realizado com sucesso!')
    return redirect(url_for('login'))

@app.route('/upload_profile_picture', methods=['POST'])
def upload_profile_picture():
    if 'firebase_user' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['firebase_user'])
    if request.method == 'POST':
        picture = request.files['profile_picture']
        filename = save_profile_picture(picture)
        if filename:
            user.profile_picture = filename
            db.session.commit()
            flash('Imagem de perfil atualizada com sucesso!')
        else:
            flash('Erro ao fazer upload da imagem.')
    
    return redirect(url_for('profile', username=user.username))

@app.route('/like_post/<int:post_id>', methods=['POST'])
def like_post(post_id):
    if 'firebase_user' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['firebase_user'])
    result = like_post_action(post_id, user)

    return jsonify(result)

@app.route('/comment_post/<int:post_id>', methods=['POST'])
def comment_post(post_id):
    if 'firebase_user' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['firebase_user'])
    content = request.form['content']
    result = comment_post_action(post_id, user, content)

    return jsonify(result)

@app.route('/share_post/<int:post_id>', methods=['POST'])
def share_post(post_id):
    if 'firebase_user' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['firebase_user'])
    post = Post.query.get(post_id)

    if post:
        new_share = Share(post_id=post.id, user_id=user.id)
        db.session.add(new_share)
        db.session.commit()
        flash('Post compartilhado com sucesso!')
    else:
        flash('Post não encontrado.')

    return redirect(url_for('home'))

@app.route('/user/<username>/followers')
def manage_followers(username):
    user = get_user_by_username(username)
    if user is None:
        flash('Usuário não encontrado.')
        return redirect(url_for('home'))

    followers_list = Follower.query.filter_by(user_id=user.id).all()
    follower_usernames = [User.query.get(f.follower_id).username for f in followers_list]

    return render_template('followers.html', user=user, followers=follower_usernames)

@app.route('/user/<username>/following')
def following(username):
    user = get_user_by_username(username)
    if user is None:
        flash('Usuário não encontrado.')
        return redirect(url_for('home'))

    following_list = Follower.query.filter_by(follower_id=user.id).all()
    following_usernames = [User.query.get(f.user_id).username for f in following_list]

    return render_template('following.html', user=user, following=following_usernames)

@app.route('/follow_user/<username>', methods=['POST'])
def follow_user(username):
    if 'firebase_user' not in session:
        return redirect(url_for('login'))

    user_to_follow = get_user_by_username(username)
    user = User.query.get(session['firebase_user'])

    if user_to_follow and user_to_follow.id != user.id:
        existing_follow = Follower.query.filter_by(user_id=user_to_follow.id, follower_id=user.id).first()
        if existing_follow:
            flash('Você já está seguindo este usuário.')
        else:
            new_follow = Follower(user_id=user_to_follow.id, follower_id=user.id)
            db.session.add(new_follow)
            db.session.commit()
            flash('Você começou a seguir este usuário!')
    else:
        flash('Erro ao seguir o usuário.')

    return redirect(url_for('profile', username=username))

@app.route('/unfollow_user/<username>', methods=['POST'])
def unfollow_user(username):
    if 'firebase_user' not in session:
        return redirect(url_for('login'))

    user_to_unfollow = get_user_by_username(username)
    user = User.query.get(session['firebase_user'])

    if user_to_unfollow:
        existing_follow = Follower.query.filter_by(user_id=user_to_unfollow.id, follower_id=user.id).first()
        if existing_follow:
            db.session.delete(existing_follow)
            db.session.commit()
            flash('Você deixou de seguir este usuário.')
        else:
            flash('Você não está seguindo este usuário.')
    else:
        flash('Erro ao deixar de seguir o usuário.')

    return redirect(url_for('profile', username=username))

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    if query:
        users = User.query.filter(User.username.ilike(f'%{query}%')).all()
        posts = Post.query.filter(Post.content.ilike(f'%{query}%')).all()
        return render_template('search_results.html', users=users, posts=posts)
    flash('Por favor, insira um termo de pesquisa válido.')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
