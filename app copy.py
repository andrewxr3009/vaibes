import uuid
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
from sqlalchemy import text

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Substitua por uma chave secreta adequada
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quifoi.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    posts = db.relationship('Post', backref='author', lazy=True)
    likes = db.relationship('Like', backref='user', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='user', lazy=True, cascade="all, delete-orphan")
    followers = db.relationship('Follower', foreign_keys='Follower.follower_id', backref='follower', lazy='dynamic')
    following = db.relationship('Follower', foreign_keys='Follower.user_id', backref='user', lazy='dynamic')
    shares = db.relationship('Share', backref='user', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    likes = db.relationship('Like', backref='post', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")
    shares = db.relationship('Share', backref='post', lazy=True)

class Share(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    post = db.relationship('Post', backref=db.backref('shares', lazy=True))
    user = db.relationship('User', backref=db.backref('shares', lazy=True))

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(280), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Follower(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'))

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

@app.route('/')
def home():
    user_agent = request.headers.get('User-Agent')
    
    # Verifica se o User-Agent indica Safari no iPhone
    if 'iPhone' in user_agent and 'Safari' in user_agent:
        if 'username' in session:
            user = get_user_by_username(session['username'])
            if user is None:
                flash('Usuário não encontrado.')
                return redirect(url_for('logout'))
            posts = Post.query.order_by(Post.timestamp.desc()).all()
            recent_users = User.query.order_by(User.id.desc()).limit(5).all()
            return render_template('ios_home.html', posts=posts, username=session['username'], recent_users=recent_users, profile_picture=user.profile_picture, user=user)
        return redirect(url_for('login'))
    else:
        if 'username' in session:
            user = get_user_by_username(session['username'])
            if user is None:
                flash('Usuário não encontrado.')
                return redirect(url_for('logout'))
            posts = Post.query.order_by(Post.timestamp.desc()).all()
            recent_users = User.query.order_by(User.id.desc()).limit(5).all()
            return render_template('home.html', posts=posts, username=session['username'], recent_users=recent_users, profile_picture=user.profile_picture, user=user)
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

@app.route('/share_post/<int:post_id>', methods=['POST'])
def share_post(post_id):
    if 'username' in session:
        user = get_user_by_username(session['username'])
        post = Post.query.get(post_id)
        if post:
            new_share = Share(post_id=post.id, user_id=user.id)
            db.session.add(new_share)
            db.session.commit()
            flash('Post compartilhado com sucesso!')
        else:
            flash('Post não encontrado.')
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/like_post/<int:post_id>', methods=['POST'])
def like_post(post_id):
    if 'username' in session:
        user = get_user_by_username(session['username'])
        post = Post.query.get(post_id)
        if post:
            existing_like = Like.query.filter_by(user_id=user.id, post_id=post_id).first()
            if existing_like:
                db.session.delete(existing_like)
                db.session.commit()
                flash('Descurtido com sucesso!')
            else:
                new_like = Like(user_id=user.id, post_id=post_id)
                db.session.add(new_like)
                db.session.commit()
                flash('Curtido com sucesso!')
        else:
            flash('Post não encontrado.')
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/comment/<int:post_id>', methods=['POST'])
def comment(post_id):
    if 'username' in session:
        content = request.form.get('content')
        if content:
            user = get_user_by_username(session['username'])
            post = Post.query.get(post_id)
            if post:
                new_comment = Comment(content=content, post_id=post_id, user_id=user.id)
                db.session.add(new_comment)
                db.session.commit()
                flash('Comentário adicionado com sucesso!')
            else:
                flash('Post não encontrado.')
        else:
            flash('O comentário não pode estar vazio.')
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/profile/<username>', methods=['GET', 'POST'])
def profile(username):
    user = get_user_by_username(username)
    if user:
        if request.method == 'POST':
            bio = request.form.get('bio')
            picture = request.files.get('profile_picture')
            if picture:
                filename = save_profile_picture(picture)
                if filename:
                    user.profile_picture = filename
            if bio:
                user.bio = bio
            db.session.commit()
            flash('Perfil atualizado com sucesso!')
        posts = Post.query.filter_by(user_id=user.id).all()
        return render_template('profile.html', user=user, posts=posts)
    flash('Usuário não encontrado.')
    return redirect(url_for('home'))

@app.route('/follow/<username>', methods=['POST'])
def follow(username):
    if 'username' in session:
        current_user = get_user_by_username(session['username'])
        user_to_follow = get_user_by_username(username)
        if user_to_follow:
            if current_user != user_to_follow:
                existing_follow = Follower.query.filter_by(user_id=user_to_follow.id, follower_id=current_user.id).first()
                if existing_follow:
                    db.session.delete(existing_follow)
                    db.session.commit()
                    flash('Deixou de seguir.')
                else:
                    new_follow = Follower(user_id=user_to_follow.id, follower_id=current_user.id)
                    db.session.add(new_follow)
                    db.session.commit()
                    flash('Seguindo agora!')
            else:
                flash('Você não pode seguir a si mesmo.')
        else:
            flash('Usuário não encontrado.')
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
