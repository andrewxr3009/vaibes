from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid
import os
from sqlalchemy import text
from post_functions import share_post, like_post, comment_post
import requests



app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Substitua por uma chave secreta adequada
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quifoi.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

GIPHY_API_KEY = 'URqPC2QH6fsA2xCx7ySJTbholry57xjy'
GIPHY_SEARCH_URL = 'https://api.giphy.com/v1/gifs/search'


# Configuração para a nova base de dados (para followers)
app.config['SQLALCHEMY_BINDS'] = {
    'follows': 'sqlite:///follows.db'
}

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
        picture_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        picture.save(picture_path)
        return new_filename
    return None

# Modelos do banco de dados
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    bio = db.Column(db.String(255))
    profile_picture = db.Column(db.String(120))  # Novo campo para a foto de perfil
    posts = db.relationship('Post', back_populates='author', lazy=True)
    likes = db.relationship('Like', back_populates='user', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', back_populates='user', lazy=True, cascade="all, delete-orphan")
    followers = db.relationship('Follower', foreign_keys='Follower.follower_id', back_populates='follower', lazy='dynamic')
    following = db.relationship('Follower', foreign_keys='Follower.user_id', back_populates='user', lazy='dynamic')
    shares = db.relationship('Share', back_populates='sharer', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    likes = db.relationship('Like', back_populates='post', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', back_populates='post', lazy=True, cascade="all, delete-orphan")
    shares = db.relationship('Share', back_populates='shared_post', lazy=True)
    author = db.relationship('User', back_populates='posts')

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    post = db.relationship('Post', back_populates='likes')
    user = db.relationship('User', back_populates='likes')

class Share(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    post = db.relationship('Post', back_populates='shares')
    user = db.relationship('User', back_populates='shares')
    
    sharer = db.relationship('User', overlaps="user", back_populates='shares')
    shared_post = db.relationship('Post', overlaps="post", back_populates='shares')


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    post = db.relationship('Post', back_populates='comments')
    user = db.relationship('User', back_populates='comments')


class Follower(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', foreign_keys=[user_id], back_populates='following')
    follower = db.relationship('User', foreign_keys=[follower_id], back_populates='followers')


# Cria os bancos de dados
def create_tables():
    with app.app_context():
        # Cria as tabelas principais
        db.create_all()
        
        # Cria as tabelas do banco de dados 'follows'
        from sqlalchemy import create_engine
        from sqlalchemy.orm import scoped_session, sessionmaker

        follows_engine = create_engine(app.config['SQLALCHEMY_BINDS']['follows'])
        follows_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=follows_engine))
        follows_metadata = db.metadata

        # Ativa a verificação de chaves estrangeiras para o banco de dados 'follows'
        with follows_engine.connect() as connection:
            connection.execute(text('PRAGMA foreign_keys=ON;'))
            follows_metadata.create_all(bind=follows_engine)

create_tables()

def get_user_by_username(username):
    return User.query.filter_by(username=username).first()

def like_post_action(post_id, user):
    from app import db, Post, Like  # Importa modelos necessários
    post = Post.query.get(post_id)
    if post:
        # Verifica se o usuário já curtiu o post
        existing_like = Like.query.filter_by(post_id=post_id, user_id=user.id).first()
        if existing_like:
            return {'status': 'error', 'message': 'Você já curtiu este post.'}

        # Adiciona a nova curtida
        new_like = Like(post_id=post.id, user_id=user.id)
        db.session.add(new_like)
        db.session.commit()

        # Retorna a nova contagem de curtidas
        like_count = Like.query.filter_by(post_id=post_id).count()
        return {'status': 'success', 'message': 'Post curtido!', 'like_count': like_count}
    return {'status': 'error', 'message': 'Post não encontrado.'}

def comment_post_action(post_id, user, content):
    from app import db, Post, Comment  # Importa modelos necessários
    post = Post.query.get(post_id)
    if post:
        new_comment = Comment(post_id=post.id, user_id=user.id, content=content)
        db.session.add(new_comment)
        db.session.commit()

        # Atualiza a contagem de comentários
        post.comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.timestamp.asc()).all()        
        db.session.commit()

        return {'status': 'success', 'message': 'Comentário adicionado!'}
    return {'status': 'error', 'message': 'Post não encontrado.'}



@app.route('/')
def home():
    user_agent = request.headers.get('User-Agent')
    
    if 'username' in session:
        user = get_user_by_username(session['username'])
        if user is None:
            flash('Usuário não encontrado.')
            return redirect(url_for('logout'))
        
        user_id = user.id
        
        # Obtém todos os posts do mais recente para o mais antigo
        posts = Post.query.order_by(Post.timestamp.asc()).all()
        
        # Itera sobre cada post para adicionar os comentários
        for post in posts:
            # Ordena os comentários do mais antigo para o mais recente
            post.comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.timestamp.asc()).all()
        
        recent_users = User.query.order_by(User.id.desc()).limit(5).all()
        
        if 'iPhone' in user_agent and 'Safari' in user_agent:
            return render_template('ios_home.html', posts=posts, username=session['username'], 
                                   recent_users=recent_users, profile_picture=user.profile_picture, 
                                   user=user, user_id=user_id)
        else:
            return render_template('home.html', posts=posts, username=session['username'], 
                                   recent_users=recent_users, profile_picture=user.profile_picture, 
                                   user=user)
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if email and password:
            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password, password):
                session['username'] = user.username
                return redirect(url_for('home'))
            else:
                flash('Login falhou. Verifique seu e-mail e senha.')
        else:
            flash('Por favor, preencha todos os campos.')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if username and email and password:
            if User.query.filter_by(email=email).first() is None:
                hashed_password = generate_password_hash(password)
                new_user = User(username=username, email=email, password=hashed_password)
                db.session.add(new_user)
                db.session.commit()
                flash('Cadastro realizado com sucesso!')
                return redirect(url_for('login'))
            else:
                flash('Email já está em uso.')
        else:
            flash('Por favor, preencha todos os campos.')
    return render_template('signup.html')

@app.route('/post', methods=['POST'])
def post():
    if 'username' in session:
        content = request.form.get('content')
        gif_url = request.form.get('gif_url')
        
        if content:
            user = get_user_by_username(session['username'])
            new_post = Post(content=content, author=user)
            db.session.add(new_post)
            db.session.commit()
            flash('Postagem criada com sucesso!')
        else:
            flash('O conteúdo do post não pode estar vazio.')
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/share_post/<int:post_id>', methods=['POST', 'GET'])
def share_post(post_id):
    if 'username' in session:
        user = get_user_by_username(session['username'])
        return share_post(post_id, user)
    return redirect(url_for('login'))

@app.route('/like_post/<int:post_id>', methods=['POST'])
def like_post_route(post_id):
    if 'username' in session:
        user = get_user_by_username(session['username'])
        response = like_post_action(post_id, user)  # Use uma função de ação para curtir
        return jsonify(response)
    return jsonify({'status': 'error', 'message': 'Usuário não autenticado.'}), 401

@app.route('/comment_post/<int:post_id>', methods=['POST'])
def comment_post(post_id):
    if 'username' in session:
        user = get_user_by_username(session['username'])
        content = request.form.get('comment_content')
        response = comment_post_action(post_id, user, content)  # Use uma função de ação para comentar
        return redirect(url_for('home'))  # Pode ser redirecionado ou retornado JSON
    return jsonify({'status': 'error', 'message': 'Usuário não autenticado.'}), 401


@app.route('/profile')
def profile():
    user_agent = request.headers.get('User-Agent')
    
    if 'username' in session:
        user = get_user_by_username(session['username'])
        if user is None:
            flash('Usuário não encontrado.')
            return redirect(url_for('logout'))

        # Define o user_id com base no usuário
        user_id = user.id

        posts = Post.query.filter_by(user_id=user.id).order_by(Post.timestamp.desc()).all()

        # Verifica se o User-Agent indica Safari no iPhone
        if 'iPhone' in user_agent and 'Safari' in user_agent:
            return render_template('ios_profile.html', user=user, posts=posts, profile_picture=user.profile_picture, user_id=user_id)
        else:
            return render_template('profile.html', user=user, posts=posts, profile_picture=user.profile_picture, user_id=user_id)
    else:
        return redirect(url_for('login'))


@app.route('/profile_settings', methods=['GET', 'POST'])
def profile_settings():
    if 'username' in session:
        user = get_user_by_username(session['username'])
        if not user:
            flash('Usuário não encontrado.')
            return redirect(url_for('logout'))

        if request.method == 'POST':
            # Atualiza a bio
            bio = request.form.get('bio')
            if bio:
                user.bio = bio

            # Atualiza a foto de perfil, se foi enviada
            if 'profile_picture' in request.files:
                picture = request.files['profile_picture']
                if picture and allowed_file(picture.filename):
                    new_picture = save_profile_picture(picture)
                    if new_picture:
                        user.profile_picture = new_picture

            # Salva as alterações no banco de dados
            db.session.commit()
            flash('Perfil atualizado com sucesso!')
            return redirect(url_for('profile', username=user.username))  # Redireciona para o perfil atualizado

        # Exibe a página de configurações de perfil (GET)
        return render_template('profile_settings.html', user=user)

    return redirect(url_for('login'))


@app.route('/search')
def search():
    if 'username' in session:
        query = request.args.get('query')
        if query:
            users = User.query.filter(User.username.like(f'%{query}%')).all()
            return render_template('search.html', users=users)
        else:
            flash('Nenhuma consulta fornecida.')
            return redirect(url_for('profile'))
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/search_gifs', methods=['GET'])
def search_gifs():
    query = request.args.get('query', '')
    if not query:
        return jsonify({'error': 'No search query provided'}), 400

    response = requests.get(GIPHY_SEARCH_URL, params={
        'api_key': GIPHY_API_KEY,
        'q': query,
        'limit': 10  # Limitando o número de GIFs retornados
    })

    if response.status_code == 200:
        gifs = response.json().get('data', [])
        return jsonify({'gifs': [{'url': gif['images']['fixed_height']['url']} for gif in gifs]})
    else:
        return jsonify({'error': 'Failed to fetch GIFs'}), response.status_code
    
@app.route('/post_gif', methods=['POST'])
def post_gif():
    gif_url = request.form.get('gif_url')
    
    if not gif_url:
        return jsonify({'success': False, 'message': 'No GIF URL provided'}), 400
    
    # Exemplo de como lidar com a URL do GIF (exibir ou salvar)
    return jsonify({'success': True, 'gif_url': gif_url})


@app.template_filter('to_datetime_string')
def to_datetime_string(value):
    if isinstance(value, datetime):
        return value.strftime('%d de %B de %Y')  # Ajuste o formato conforme necessário
    return value

# Rota para exibir os detalhes do post
@app.route('/post/<int:post_id>', methods=['GET'])
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)
    comments = Comment.query.filter_by(post_id=post_id).all()
    return render_template('post_detail.html', post=post, comments=comments)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
