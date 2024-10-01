from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid
import os
import requests
import io
import firebase_admin
from firebase_admin import credentials, auth, firestore, messaging
import bcrypt
from google.cloud import storage
import json
from flask_cors import CORS

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

CORS(app)

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
class User(db.Model):
    __tablename__ = 'user'  
    id = db.Column(db.Integer, primary_key=True)
    firebase_id = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    bio = db.Column(db.String(255))
    profile_picture = db.Column(db.String(255))
    
    # Relacionamentos
    posts = db.relationship('Post', back_populates='user')
    comments = db.relationship('Comment', back_populates='user')
    likes = db.relationship('Like', back_populates='user', lazy=True, cascade="all, delete-orphan")
    shares = db.relationship('Share', back_populates='sharer', lazy=True)
    device_token = db.Column(db.Text)  
    subscription_info = db.Column(db.Text)  # Para armazenar a inscrição do usuário 
    followers = db.relationship('Follower', foreign_keys='Follower.follower_id', back_populates='follower', lazy='dynamic')
    following = db.relationship('Follower', foreign_keys='Follower.user_id', back_populates='user', lazy='dynamic')

    def is_following(self, user):
        """Verifica se o usuário atual está seguindo o usuário passado."""
        return Follower.query.filter_by(user_id=user.id, follower_id=self.id).count() > 0



class Follower(db.Model):
    __tablename__ = 'follower'  
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', foreign_keys=[user_id], back_populates='following')
    follower = db.relationship('User', foreign_keys=[follower_id], back_populates='followers')


class Post(db.Model):
    __tablename__ = 'post'  
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relacionamentos
    likes = db.relationship('Like', back_populates='post', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', back_populates='post', lazy=True, cascade="all, delete-orphan")
    shares = db.relationship('Share', back_populates='shared_post', lazy=True)
    user = db.relationship('User', back_populates='posts')
    impressions = db.Column(db.Integer, default=0)  
    gif_url = db.Column(db.String, nullable=True)  
    hashtags = db.relationship('PostHashtag', backref='post', lazy=True)  
    views = db.Column(db.Integer, default=0)


class Comment(db.Model):
    __tablename__ = 'comment'  
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relacionamentos
    user = db.relationship('User', back_populates='comments')
    post = db.relationship('Post', back_populates='comments')


class Share(db.Model):
    __tablename__ = 'share'  
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    shared_post = db.relationship('Post', back_populates='shares')
    sharer = db.relationship('User', back_populates='shares', foreign_keys=[user_id])


class Like(db.Model):
    __tablename__ = 'like'  
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    post = db.relationship('Post', back_populates='likes')
    user = db.relationship('User', back_populates='likes')


class Notification(db.Model):
    __tablename__ = 'notification'  
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    user = db.relationship('User', backref='notifications')
    post = db.relationship('Post', backref='notifications')


class Hashtag(db.Model):
    __tablename__ = 'hashtag'  
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    post_count = db.Column(db.Integer, default=0)  
    posts = db.relationship('PostHashtag', backref='hashtag', lazy=True)


class PostHashtag(db.Model):
    __tablename__ = 'post_hashtag'  
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    hashtag_id = db.Column(db.Integer, db.ForeignKey('hashtag.id'), nullable=False)



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

def create_notification(user_id, message):
    notification = Notification(user_id=user_id, message=message)
    db.session.add(notification)
    db.session.commit()

def like_post_action(post_id, user):
    post = Post.query.get(post_id)  # Certifique-se de obter o objeto Post corretamente
    if not post:
        return {"status": "error", "message": "Post não encontrado."}

    if post:
        existing_like = Like.query.filter_by(post_id=post_id, user_id=user.id).first()
        if existing_like:
            return {'status': 'error', 'message': 'Você já curtiu este post.'}

        new_like = Like(post_id=post.id, user_id=user.id)
        db.session.add(new_like)
        db.session.commit()

        # Notificar o autor do post sobre a nova curtida
        post_owner = User.query.get(post.user_id)  # Identificar o dono do post
        if post_owner and post_owner.id != user.id:  # Verifica se o post não é do usuário que curtiu
            notification_message = f"{user.username} curtiu seu post."
            notification = Notification(user_id=post_owner.id, post_id=post.id, message=notification_message)
            db.session.add(notification)
            db.session.commit()  # Certifique-se de salvar a notificação

        like_count = Like.query.filter_by(post_id=post_id).count()
        return {'status': 'success', 'like_count': like_count}

    return {'status': 'error', 'message': 'Post não encontrado.'}


def comment_post_action(post_id, user, content):
    post = Post.query.get(post_id)
    if post and content:
        new_comment = Comment(post_id=post.id, user_id=user.id, content=content)
        db.session.add(new_comment)
        db.session.commit()

        # Notificar o autor do post sobre o novo comentário
        if post.p.author != user.id:  # Evita notificar o próprio usuário
            create_notification(post.p.author, f"{user.username} comentou em seu post.")

        comments = Comment.query.filter_by(post_id=post_id).all()
        comments_data = [{'username': c.c_user.username, 'content': c.content} for c in comments]
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
    posts = Post.query.order_by(Post.timestamp.desc()).all()
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
    print(f"Username recebido: {username}")  # Debug
    user = get_user_by_username(username)
    if user is None:
        flash('Usuário não encontrado.')
        return redirect(url_for('home'))

    try:
        posts = Post.query.filter_by(user_id=user.id).order_by(Post.timestamp.desc()).all()
    except Exception as e:
        print(f"Erro ao buscar posts: {e}")
    posts = []  # Ou redirecionar para uma página de erro
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



import pusher

# Inicializa o cliente Pusher
pusher_client = pusher.Pusher(
    app_id='1873813',
    key='125aed71fd441d77aae7',
    secret='c72a17eb22ed7d06c4d4',
    cluster='sa1',
    ssl=True
)

@app.route('/post', methods=['GET', 'POST'])
def create_post():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        content = request.form['content']
        gif_url = request.form['gif_url']
        hashtags_input = request.form.get('hashtags', '')
        hashtags = [h.strip() for h in hashtags_input.split(',') if h.strip()]  # Captura hashtags do formulário

        if content:
            new_post = Post(content=content, gif_url=gif_url, user_id=user.id)
            db.session.add(new_post)

            for hashtag_name in hashtags:
                # Remover o '#' do nome da hashtag, se presente
                if hashtag_name.startswith('#'):
                    hashtag_name = hashtag_name[1:]

                hashtag = Hashtag.query.filter_by(name=hashtag_name).first()
                if not hashtag:
                    hashtag = Hashtag(name=hashtag_name, post_count=1)  # Criar nova hashtag
                    db.session.add(hashtag)
                else:
                    hashtag.post_count += 1  # Incrementar contador de posts
                db.session.flush()  # Permitir que o ID da hashtag esteja disponível

                # Vincular post e hashtag
                post_hashtag = PostHashtag(post_id=new_post.id, hashtag_id=hashtag.id)
                db.session.add(post_hashtag)

            # Notificar todos os usuários
            all_users = User.query.all()
            for recipient in all_users:
                if recipient.id != user.id:
                    notification = Notification(user_id=recipient.id, post_id=new_post.id, message=f"{user.username} criou um novo post.")
                    db.session.add(notification)

                    # Envia o evento para o Pusher
                    pusher_client.trigger('my-channel', 'my-event', {'message': f"{user.username} criou um novo post."})

            db.session.commit()  # Salvar todas as notificações
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

                # Obter o token de dispositivo (você deve implementar isso na parte do cliente)
                device_token = request.form.get('device_token')

                # Verificar o usuário no banco de dados
                user = User.query.filter_by(email=email).first()
                if not user:
                    flash("Usuário não encontrado no banco de dados.", "danger")
                    return redirect(url_for('login'))

                # Atualizar o token de dispositivo no banco de dados
                user.device_token = device_token
                db.session.commit()

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
    post = Post.query.get(post_id)

    # Inicializa post_owner
    post_owner = post.user_id if post else None

    # Tente realizar a ação de curtir o post
    result = like_post_action(post_id, user)

    if result.get('status') == 'success':
        post = Post.query.get(post_id)  # Obter o post que foi curtido
        post_owner = User.query.get(post.user_id)  # Identificar o dono do post

        # Enviar notificação ao dono do post
        if post_owner and post_owner.id != user.id:  # Verifica se o post não é do usuário que curtiu
            notification_message = f"{user.username} curtiu seu post."
            notification = Notification(user_id=post_owner.id, post_id=post.id, message=notification_message)
            db.session.add(notification)
            db.session.commit()  # Certifique-se de salvar a notificação

    return jsonify(result)


@app.route('/add_comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Usuário não autenticado.'})

    user = User.query.get(session['user_id'])
    data = request.get_json()
    content = data.get('content')

    if not content:
        return jsonify({'status': 'error', 'message': 'O comentário não pode estar vazio.'})

    post = Post.query.get(post_id)
    if post:
        new_comment = Comment(content=content, user_id=user.id, post_id=post_id)
        db.session.add(new_comment)

        # Enviar notificação ao dono do post
        post_owner = User.query.get(post.user_id)  # Identificar o dono do post
        if post_owner and post_owner.id != user.id:  # Verifica se o post não é do comentarista
            notification_message = f"{user.username} comentou no seu post."
            notification = Notification(user_id=post_owner.id, post_id=post.id, message=notification_message)
            db.session.add(notification)

        db.session.commit()

        return jsonify({
            'status': 'success',
            'comment': {
                'author': user.username,
                'content': new_comment.content
            }
        })
    return jsonify({'status': 'error', 'message': 'Post não encontrado.'})

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
def toggle_follow(username):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Obtém o usuário que deseja seguir usando o username
    user_to_follow = User.query.filter_by(username=username).first()
    current_user = User.query.get(session['user_id'])

    if user_to_follow and user_to_follow.id != current_user.id:
        # Verifica se já está seguindo
        existing_follow = Follower.query.filter_by(user_id=user_to_follow.id, follower_id=current_user.id).first()
        
        if existing_follow:
            # Deixar de seguir
            db.session.delete(existing_follow)
            db.session.commit()
            message = 'Você deixou de seguir este usuário.'
            following_status = False
        else:
            # Seguir
            new_follow = Follower(user_id=user_to_follow.id, follower_id=current_user.id)
            db.session.add(new_follow)
            db.session.commit()
            message = 'Você começou a seguir este usuário!'
            following_status = True
            
        return jsonify({'message': message, 'following': following_status}), 200

    return jsonify({'message': 'Erro ao processar a solicitação.'}), 400


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
    user = User.query.get(session['user_id'])

    return render_template('search.html', user=user)

@app.route('/search/results', methods=['GET'])
def search_results():
    query = request.args.get('query')
    filter_option = request.args.get('filter', 'all')  # Filtrar por padrão para 'todos'
    user = User.query.get(session['user_id'])
    current_user = User.query.get(session['user_id'])
    
    
    users, posts, hashtags = [], [], []
    
    if query:
        # Lógica de filtragem com base na seleção do filtro
        if filter_option == 'people' or filter_option == 'all':
            users = User.query.filter(User.username.ilike(f'%{query}%')).all()
        
        if filter_option == 'posts' or filter_option == 'all':
            posts = Post.query.filter(Post.content.ilike(f'%{query}%')).all()
        
        if filter_option == 'hashtags' or filter_option == 'all':
            posts_with_hashtags = Post.query.filter(Post.content.ilike(f'%#{query}%')).all()
            hashtags = [f'#{query}'] if posts_with_hashtags else []
        
        # Caso o filtro seja 'locations', ainda não implementado
        if filter_option == 'locations':
            # Exemplo: lógicas futuras para busca por locais
            pass
        
        return render_template('search_results.html', users=users, user=user, current_user=current_user, posts=posts, hashtags=hashtags, query=query)
    
    flash('Por favor, insira um termo de pesquisa válido.', 'warning')
    return redirect(url_for('show_search_page'))




@app.route('/post/<int:post_id>', methods=['GET'])
def post_detail(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    post = Post.query.get(post_id)
    if post is None:
        flash('Post não encontrado.', 'danger')
        return redirect(url_for('home'))

    # Incrementa a contagem de visualizações
    post.views += 1
    db.session.commit()

    # Obtém os comentários associados ao post, ordenados por timestamp
    comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.timestamp.asc()).all()

    # Obtém o usuário que criou o post
    user_to_follow = User.query.get(post.user_id)  # Corrigido para obter o usuário com base no user_id

    # Obtém o usuário atual
    user = User.query.get(session['user_id'])

    # Verifica se o usuário atual está seguindo o autor do post
    is_following = user.following.filter(Follower.user_id == user_to_follow.id).count() > 0 if user_to_follow else False

    return render_template('post_detail.html', post=post, comments=comments, user=user, user_to_follow=user_to_follow, is_following=is_following)

@app.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    notifications = Notification.query.filter_by(user_id=user.id).order_by(Notification.timestamp.desc()).all()

    # Debug: Imprimir as notificações para verificar se estão sendo carregadas
    print(notifications)

    return render_template('notifications.html', user=user, notifications=notifications)


@app.route('/mark_notification_read/<int:notification_id>', methods=['POST'])
def mark_notification_read(notification_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    notification = Notification.query.get(notification_id)
    if notification and notification.user_id == session['user_id']:
        notification.read = True
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Notificação marcada como lida.'})
    
    return jsonify({'status': 'error', 'message': 'Notificação não encontrada ou acesso negado.'})

@app.route('/hashtag_suggestions')
def hashtag_suggestions():
    query = request.args.get('query', '')
    hashtags = Hashtag.query.filter(Hashtag.name.like(f'%{query}%')).all()
    return jsonify(hashtags=[{'name': h.name, 'post_count': h.post_count} for h in hashtags])

@app.route('/hashtag/<string:hashtag_name>')
def view_hashtag_posts(hashtag_name):
    # Remover o '#' se necessário
    if hashtag_name.startswith('#'):
        hashtag_name = hashtag_name[1:]

    print(hashtag_name)
    user = User.query.get(session['user_id'])
    hashtag = Hashtag.query.filter_by(name=hashtag_name).first()
    if hashtag:
        posts = Post.query.join(PostHashtag).filter(PostHashtag.hashtag_id == hashtag.id).all()
        return render_template('hashtags.html', posts=posts, hashtag=hashtag_name, user=user)
    else:
        flash('Hashtag não encontrada.', 'danger')
        return redirect(url_for('home'))



@app.route('/delete_post/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    # Busca o post pelo ID
    post = Post.query.get_or_404(post_id)

    # Verifica se o usuário tem permissão para excluir o post
    if post.author.id != session['user_id']:
        return jsonify(success=False, message="Você não tem permissão para excluir este post."), 403

    # Exclui todas as notificações associadas ao post
    Notification.query.filter_by(post_id=post_id).delete()

    # Exclui o post
    db.session.delete(post)
    db.session.commit()

    return jsonify(success=True)


@app.route('/insights/<int:post_id>')
def insights(post_id):
    # Verifica se o usuário está autenticado
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Busca o post pelo ID
    user = User.query.get(session['user_id'])
    post = Post.query.get(post_id)
    if post is None:
        flash('Post não encontrado.', 'danger')
        return redirect(url_for('home'))

    # Verifica se o usuário é o autor do post
    if post.user_id != session['user_id']:
        flash('Você não tem permissão para acessar os insights deste post.', 'danger')
        return redirect(url_for('home'))
     # Ou o método que você usa para contar as visualizações
    like_count = len(post.likes)  # Conta as curtidas associadas ao post
    impression_count = post.impressions  # Adicione esta propriedade ao modelo de Post
    view_count = post.views

    # Renderiza a página de insights com as informações do post
    return render_template('insights.html', post=post, user=user, like_count=like_count, impression_count=impression_count, view_count=view_count)

@app.route('/ads.txt')
def ads():
    return send_from_directory('static', 'ads.txt')

@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/firebase-messaging-sw.js')
def fbm():
    return send_from_directory('static', 'firebase-messaging-sw.js')

@app.route('/favicon.ico')
def fiv():
    return send_from_directory('static', 'favicon.ico')

@app.route('/service-worker.js', endpoint='service_worker')
def fiv():
    return send_from_directory('static', 'service-worker.js')



@app.route('/increment_impression/<int:post_id>', methods=['POST'])
def increment_impression(post_id):
    post = Post.query.get_or_404(post_id)
    post.impressions += 1  # Assegure-se que a coluna 'impressions' exista no seu modelo Post
    db.session.commit()
    return jsonify(success=True)

@app.route('/profile_settings', methods=['POST', 'GET'])
def profile_settings():
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        # Atualizar bio
        bio = request.form.get('bio')
        if bio:
            user.bio = bio
            flash('Bio atualizada com sucesso!', 'success')

        # Alterar senha
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        if old_password and new_password:
            if bcrypt.checkpw(old_password.encode('utf-8'), user.password.encode('utf-8')):
                user.password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                flash('Senha alterada com sucesso!', 'success')
            else:
                flash('Senha antiga incorreta!', 'danger')

        # Atualizar foto de perfil
        picture = request.files.get('profile_picture')
        if picture and allowed_file(picture.filename):
            profile_picture_url = save_profile_picture(picture)
            user.profile_picture = profile_picture_url
            flash('Foto de perfil atualizada!', 'success')

        db.session.commit()
        return redirect(url_for('profile_settings'))

    return render_template('profile_settings.html', user=user)

@app.route('/save-token', methods=['POST'])
def save_token():
    data = request.get_json()
    token = data.get('token')
    user_id = session['user_id']  # Supondo que o usuário esteja autenticado
    print(f'Token recebido: {token}')

    user = User.query.get(user_id)
    user.device_token = token  # Armazena o token
    db.session.commit()
    return jsonify({'success': True}), 200




# Inicialização da aplicação
if __name__ == '__main__':
    app.run(debug=True)