from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Float, create_engine
from sqlalchemy.orm import relationship, sessionmaker
from flask_sqlalchemy import SQLAlchemy
import spacy
import psycopg2
from apscheduler.schedulers.background import BackgroundScheduler
import time
import random  # Importando a biblioteca random

# Configuração da conexão com o banco de dados Supabase
DATABASE_URI = 'postgresql+psycopg2://postgres.txyhqnbmlpcywyapxypm:5edqw3n4lhxCacLm@aws-0-us-west-1.pooler.supabase.com:6543/postgres'
engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()
db = SQLAlchemy()

# Tentativa de carregar os modelos de linguagem
try:
    nlp_en = spacy.load('en_core_web_sm')
    nlp_pt = spacy.load('pt_core_news_sm')
except Exception as e:
    print(f'Erro ao carregar os modelos de linguagem: {e}')

# Definição das tabelas no SQLAlchemy
class User(db.Model):
    __tablename__ = 'user'  
    id = db.Column(db.Integer, primary_key=True)
    firebase_id = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    bio = db.Column(db.String(255))
    interests = db.Column(db.String(255), nullable=True)  # Interesses do usuário
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

# Função para calcular a relevância para todos os usuários
def calculate_relevance_for_all_users(session):
    print("Iniciando cálculo de relevância...")
    users = session.query(User).all()  # Agora a classe User está definida corretamente
    posts = session.query(Post).all()

    # Embaralha a lista de posts
    random.shuffle(posts)

    for user in users:
        print(f'Calculando relevância para o usuário: {user.username} (ID: {user.id})')

        if not user.interests:
            print(f'Interesses do usuário {user.username} estão vazios. Pulando...')
            continue

        # Garantir que `user.interests` seja uma lista ou uma string
        if isinstance(user.interests, str):
            user_interests = set(user.interests.split(','))
        elif isinstance(user.interests, list):
            user_interests = set(user.interests)
        else:
            print(f'Tipo inesperado para interesses do usuário {user.username}: {type(user.interests)}')
            continue

        # Limpar relevâncias anteriores
        session.query(Relevance).filter(Relevance.user_id == user.id).delete()

        for post in posts:
            relevance_score = 0

            if post.user_id == user.id:
                continue

            # Calcular relevância com base em likes e comentários
            relevance_score += 0.5 * len(post.likes or [])
            relevance_score += 0.5 * len(post.comments or [])

            # Relevância baseada em interesses
            post_tags = set(post.tags.split(',')) if post.tags else set()
            common_interests = user_interests.intersection(post_tags)
            if common_interests:
                relevance_score += 1.0 * len(common_interests)

            # Salvar relevância calculada
            new_relevance = Relevance(user_id=user.id, post_id=post.id, relevance_score=relevance_score)
            session.add(new_relevance)

        print(f'Relevância calculada para o usuário {user.username}: {len(posts)} posts processados.')

    session.commit()
    print('Cálculo de relevância concluído!')


# Agendando a execução imediata e depois a cada 5 minutos
def schedule_relevance_calculation():
    scheduler = BackgroundScheduler(daemon=False)

    # Executa imediatamente na inicialização e depois a cada 5 minutos
    print("Executando o job imediatamente e depois a cada 5 minutos...")  
    scheduler.add_job(lambda: calculate_relevance_for_all_users(session), 'interval', minutes=5, next_run_time=datetime.now())
    scheduler.start()
    print("Scheduler iniciado com sucesso")

# Iniciar a execução agendada
if __name__ == '__main__':
    calculate_relevance_for_all_users(session)  # Executar imediatamente na inicialização
    schedule_relevance_calculation()  # Agendar para cada 5 minutos

    try:
        while True:
            time.sleep(60)  # Manter o processo ativo
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler encerrado.")
