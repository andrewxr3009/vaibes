import spacy
from spacy_langdetect import LanguageDetector
from spacy.language import Language
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Função para adicionar LanguageDetector ao pipeline
@Language.factory('language_detector')
def create_language_detector(nlp, name):
    return LanguageDetector()

# Carregar o modelo NLP para inglês e português
nlp_en = spacy.load("en_core_web_sm")
nlp_pt = spacy.load("pt_core_news_sm")

# Adicionar o detector de idioma ao pipeline de NLP
nlp_en.add_pipe('language_detector', last=True)
nlp_pt.add_pipe('language_detector', last=True)

# Dicionário com os tópicos e palavras-chave
TOPIC_TAGS = {
    'esportes': ['jogo', 'futebol', 'basquete', 'esportes', 'campeonato', 'brasileirão', 'fla'],
    'notícias': ['notícia', 'política', 'economia', 'brasil', 'mundo', 'governo', 'eleições'],
    'música': ['música', 'cantor', 'banda', 'álbum', 'show', 'festival'],
    'entretenimento': ['filme', 'cinema', 'série', 'ator', 'atriz', 'celebridade', 'tv'],
    'tecnologia': ['tecnologia', 'inovação', 'startup', 'software', 'hardware', 'ciência', 'teste', 'tags','algorítimo' ,'vaibes', 'disponível', 'próximo', 'atualização' ],
    'geek': ['geek', 'jogos', 'videogame', 'anime', 'hq', 'quadrinhos', 'mangá'],
    'cultura': ['cultura', 'arte', 'livro', 'dança', 'teatro', 'literatura', 'museu']
}


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres.txyhqnbmlpcywyapxypm:5edqw3n4lhxCacLm@aws-0-us-west-1.pooler.supabase.com:6543/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'user'  
    id = db.Column(db.Integer, primary_key=True)
    firebase_id = db.Column(db.String(255), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    bio = db.Column(db.String(255))
    interests = db.Column(db.String(255), nullable=True)  # Coluna de interesses como lista de strings
    profile_picture = db.Column(db.String(255))
    
    # Relacionamentos
    posts = db.relationship('Post', back_populates='user', lazy=True)
    # (outras relações...)

class Post(db.Model):
    __tablename__ = 'post'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', back_populates='posts')  # Adicionando esta linha
    tags = db.Column(db.String(500), nullable=True)
    assunto = db.Column(db.String(255), nullable=True)  # Nova coluna para armazenar o assunto
    impressions = db.Column(db.Integer, default=0)
    gif_url = db.Column(db.String, nullable=True)
    views = db.Column(db.Integer, default=0)
    def generate_tags(self):
        # Detect language
        doc = nlp_en(self.content)
        lang = doc._.language['language']
        
        if lang == 'pt':
            doc = nlp_pt(self.content)

        # Generate tags from the post content
        tags = [token.lemma_.lower() for token in doc if token.is_alpha and not token.is_stop]
        return tags
    def determine_assunto(self, tags):
        # Carregar palavras-chave dos tópicos em documentos NLP
        topic_docs = {topic: nlp_en(' '.join(keywords)) for topic, keywords in TOPIC_TAGS.items()}
        post_doc = nlp_en(' '.join(tags))

        best_topic = 'outros'
        best_similarity = 0.0

        # Comparar a similaridade entre as tags e os tópicos
        for topic, doc in topic_docs.items():
            similarity = post_doc.similarity(doc)
            if similarity > best_similarity:
                best_similarity = similarity
                best_topic = topic

        return best_topic

# Criar a sessão para executar queries
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
Session = sessionmaker(bind=engine)
session = Session()

def process_posts_without_tags_or_assunto():
    # Pegar posts sem tags ou sem assunto
    posts = session.query(Post).filter((Post.tags.is_(None)) | (Post.assunto.is_(None))).all()

    for post in posts:
        # Gerar tags
        tags = post.generate_tags()
        if tags:
            # Atualizar as tags do post
            post.tags = ','.join(tags)
            
            # Determinar o assunto com base nas tags
            assunto = post.determine_assunto(tags)
            post.assunto = assunto
            
            session.add(post)
            print(f"Post ID {post.id} atualizado com tags: {tags} e assunto: {assunto}")
    
    # Commitar as mudanças no banco de dados
    session.commit()
    print("Processamento completo.")


def process_post(post):
    # Gerar tags
    tags = post.generate_tags()
    if tags:
        # Atualizar as tags do post
        post.tags = ','.join(tags)
        
        # Determinar o assunto com base nas tags
        assunto = post.determine_assunto(tags)
        post.assunto = assunto
        
        session.add(post)
        print(f"Post ID {post.id} atualizado com tags: {tags} e assunto: {assunto}")
        
    # Commitar as mudanças no banco de dados
    session.commit()



if __name__ == '__main__':
    with app.app_context():
        process_posts_without_tags_or_assunto()
