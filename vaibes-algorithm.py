from sqlalchemy import create_engine, Column, Integer, ForeignKey, Float, String, ARRAY
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.orm import relationship
import psycopg2
import time

# Configuração da conexão com o banco de dados Supabase
DATABASE_URI = 'postgresql+psycopg2://postgres.txyhqnbmlpcywyapxypm:5edqw3n4lhxCacLm@aws-0-us-west-1.pooler.supabase.com:6543/postgres'
engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()

# Base declarativa
Base = declarative_base()

# Definição das classes com base nas estruturas do banco de dados
class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    interests = Column(ARRAY(String), nullable=True)  # Coluna de interesses como lista de strings

class Post(Base):
    __tablename__ = 'post'
    id = Column(Integer, primary_key=True)
    tags = Column(ARRAY(String), nullable=True)  # Coluna de tags como lista de strings

class Like(Base):
    __tablename__ = 'like'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    post_id = Column(Integer, ForeignKey('post.id'), nullable=False)

class Comment(Base):
    __tablename__ = 'comment'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    post_id = Column(Integer, ForeignKey('post.id'), nullable=False)

class Relevance(Base):
    __tablename__ = 'relevance'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    post_id = Column(Integer, ForeignKey('post.id'), nullable=False)
    relevance_score = Column(Float, nullable=False)

# Função para calcular a relevância dos posts para um único usuário
def calculate_relevance_for_user(session, user_id):
    user = session.query(User).filter(User.id == user_id).first()

    # Recupera os posts que o usuário curtiu
    liked_posts = session.query(Like).filter(Like.user_id == user_id).all()
    liked_post_ids = {like.post_id for like in liked_posts}

    # Recupera os posts que o usuário comentou
    commented_posts = session.query(Comment).filter(Comment.user_id == user_id).all()
    commented_post_ids = {comment.post_id for comment in commented_posts}

    # Recupera todos os posts
    all_posts = session.query(Post).all()

    # Dicionário para armazenar a relevância dos posts
    relevance_dict = {}

    for post in all_posts:
        relevance_score = 0
        
        # Aumenta a relevância se o post foi curtido
        if post.id in liked_post_ids:
            relevance_score += 1.0

        # Aumenta a relevância se o post foi comentado
        if post.id in commented_post_ids:
            relevance_score += 1.0

        # Verifica se o post possui tags relacionadas aos interesses do usuário
        if user.interests:
            for interest in user.interests:
                if post.tags and interest in post.tags:
                    relevance_score += 0.5

        relevance_dict[post.id] = relevance_score

    for post_id, score in relevance_dict.items():
        relevance_entry = session.query(Relevance).filter_by(user_id=user_id, post_id=post_id).first()
        if relevance_entry:
            relevance_entry.relevance_score = score
        else:
            relevance_entry = Relevance(user_id=user_id, post_id=post_id, relevance_score=score)
            session.add(relevance_entry)

    session.commit()

# Função para calcular a relevância dos posts para todos os usuários com progresso
def calculate_relevance_for_all_users(session):
    start_time = time.time()

    # Recupera todos os usuários
    all_users = session.query(User).all()
    total_users = len(all_users)

    for i, user in enumerate(all_users, 1):
        calculate_relevance_for_user(session, user.id)
        
        # Calcula o progresso
        progress = (i / total_users) * 100
        elapsed_time = time.time() - start_time
        remaining_time = (elapsed_time / i) * (total_users - i)

        print(f"Processando usuário {i}/{total_users} ({progress:.2f}% concluído).")
        print(f"Tempo estimado restante: {remaining_time:.2f} segundos.")

    total_time = time.time() - start_time
    print(f"Processo concluído em {total_time:.2f} segundos.")

# Exemplo de uso para calcular a relevância para todos os usuários
calculate_relevance_for_all_users(session)

# Cria as tabelas no banco de dados, se necessário
Base.metadata.create_all(engine)
