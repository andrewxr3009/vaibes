from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Float, create_engine
from sqlalchemy.orm import relationship
from flask_sqlalchemy import SQLAlchemy
import spacy
from sqlalchemy.orm import sessionmaker
import psycopg2

# Configuração da conexão com o banco de dados Supabase
DATABASE_URI =  'postgresql+psycopg2://postgres.txyhqnbmlpcywyapxypm:5edqw3n4lhxCacLm@aws-0-us-west-1.pooler.supabase.com:6543/postgres'
engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()
db = SQLAlchemy()

# Carrega os modelos de linguagem
nlp_en = spacy.load('en_core_web_sm')
nlp_pt = spacy.load('pt_core_news_sm')

class User(db.Model):
    __tablename__ = 'user'  
    id = db.Column(db.Integer, primary_key=True)
    firebase_id = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    bio = db.Column(db.String(255))
    interests = db.Column(db.String(255), nullable=True)
    profile_picture = db.Column(db.String(255))
    likes = db.relationship('Like', back_populates='user', lazy=True, cascade="all, delete-orphan")
    posts = db.relationship('Post', back_populates='user', lazy=True)
    relevance = db.relationship('Relevance', back_populates='user', lazy=True)
    comments = db.relationship('Comment', back_populates='user', lazy=True)

class Post(db.Model):
    __tablename__ = 'post'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='posts')
    tags = db.Column(db.String(500), nullable=True)
    assunto = db.Column(db.String(255), nullable=True)
    impressions = db.Column(db.Integer, default=0)
    gif_url = db.Column(db.String, nullable=True)
    views = db.Column(db.Integer, default=0)
    likes = db.relationship('Like', back_populates='post', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', back_populates='post', lazy=True, cascade="all, delete-orphan")

class Comment(db.Model):
    __tablename__ = 'comment'  
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user = db.relationship('User', back_populates='comments')
    post = db.relationship('Post', back_populates='comments')

class Like(db.Model):
    __tablename__ = 'like'  
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    post = db.relationship('Post', back_populates='likes')
    user = db.relationship('User', back_populates='likes')

class Relevance(db.Model):
    __tablename__ = 'relevance'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    post_id = Column(Integer, ForeignKey('post.id'), nullable=False)
    relevance_score = Column(Float, nullable=False)

    user = relationship('User', back_populates='relevance')
    post = relationship('Post')

def calculate_relevance_for_all_users(session):
    users = session.query(User).all()
    posts = session.query(Post).all()

    for user in users:
        print(f'Calculando relevância para o usuário: {user.username} (ID: {user.id})')

        # Tratar caso os interesses sejam uma lista vazia
        if user.interests is None or (isinstance(user.interests, list) and not user.interests):
            print(f'Interesses do usuário {user.username} estão vazios. Pulando...')
            continue
        
        # Limpar relevâncias anteriores
        session.query(Relevance).filter(Relevance.user_id == user.id).delete()
        
        for post in posts:
            relevance_score = 0
            
            if post.user_id == user.id:
                continue
            
            # Calcular a relevância com base em likes e comentários
            relevance_score += 0.5 * len(post.likes) if post.likes else 0
            relevance_score += 0.5 * len(post.comments) if post.comments else 0
            
            new_relevance = Relevance(user_id=user.id, post_id=post.id, relevance_score=relevance_score)
            session.add(new_relevance)

        print(f'Relevância calculada para o usuário {user.username}: {len(posts)} posts processados.')
    
    session.commit()
    print('Cálculo de relevância concluído!')

# Exemplo de uso
calculate_relevance_for_all_users(session)
