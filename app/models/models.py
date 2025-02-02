from app.extensions import db
from datetime import datetime
# import spacy
# from spacy_langdetect import LanguageDetector
# from spacy.language import Language

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
    posts = db.relationship('Post', back_populates='user')
    comments = db.relationship('Comment', back_populates='user')
    likes = db.relationship('Like', back_populates='user', lazy=True, cascade="all, delete-orphan")
    shares = db.relationship('Share', back_populates='sharer', lazy=True)
    device_token = db.Column(db.Text)  
    subscription_info = db.Column(db.Text)  # Para armazenar a inscrição do usuário 
    followers = db.relationship('Follower', foreign_keys='Follower.follower_id', back_populates='follower', lazy='dynamic')
    
    # Relacionamentos de mensagens
    messages_sent = db.relationship(
        "Message", back_populates="sender", foreign_keys='Message.sender_id'
    )
    messages_received = db.relationship(
        'Message', back_populates='receiver', lazy='dynamic', foreign_keys='Message.receiver_id'
    )
    
    # Relacionamento de quem o usuário está seguindo
    following = db.relationship('Follower', foreign_keys='Follower.user_id', back_populates='user', lazy='dynamic')

    def is_following(self, user_id):
        """Verifica se o usuário atual está seguindo o usuário passado usando o ID."""
        return Follower.query.filter_by(user_id=user_id, follower_id=self.id).count() > 0

class Message(db.Model):
    __tablename__ = 'message'  
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relacionamentos
    sender = db.relationship('User', foreign_keys=[sender_id], back_populates='messages_sent')
    receiver = db.relationship('User', foreign_keys=[receiver_id], back_populates='messages_received')



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
    tags = db.Column(db.String(500), nullable=True)  # Coluna de tags como lista de strings
    assunto = db.Column(db.String(255), nullable=True)  # Nova coluna para armazenar o assunto
    img_url = db.Column(db.String, nullable=True)  # Novo campo para armazenar URL da imagem
    
    # Relacionamentos
    likes = db.relationship('Like', back_populates='post', lazy=True, cascade="all, delete-orphan")
    comments = db.relationship('Comment', back_populates='post', lazy=True, cascade="all, delete-orphan")
    shares = db.relationship('Share', back_populates='shared_post', lazy=True)
    user = db.relationship('User', back_populates='posts')
    impressions = db.Column(db.Integer, default=0)  
    gif_url = db.Column(db.String, nullable=True)  
    hashtags = db.relationship('PostHashtag', backref='post', lazy=True)  
    views = db.Column(db.Integer, default=0)
    
    def generate_tags(self):
        # Detect language
        # doc = nlp_en(self.content)
        # lang = doc._.language['language']
        
        # if lang == 'pt':
        #     doc = nlp_pt(self.content)

        # Generate tags from the post content
        # tags = [token.lemma_.lower() for token in doc if token.is_alpha and not token.is_stop]
        # return tags
        pass
    
    def determine_assunto(self, tags):
        # Carregar palavras-chave dos tópicos em documentos NLP
        # topic_docs = {topic: nlp_en(' '.join(keywords)) for topic, keywords in TOPIC_TAGS.items()}
        # post_doc = nlp_en(' '.join(tags))

        best_topic = 'outros'
        best_similarity = 0.0

        # Comparar a similaridade entre as tags e os tópicos
        # for topic, doc in topic_docs.items():
        #     similarity = post_doc.similarity(doc)
        #     if similarity > best_similarity:
        #         best_similarity = similarity
        #         best_topic = topic

        return best_topic

# @Language.factory('language_detector')
# def create_language_detector(nlp, name):
#     return LanguageDetector()

# Carregar o modelo NLP para inglês e português
# nlp_en = spacy.load("en_core_web_sm")
# nlp_pt = spacy.load("pt_core_news_sm")

# Adicionar o detector de idioma ao pipeline de NLP
# nlp_en.add_pipe('language_detector', last=True)
# nlp_pt.add_pipe('language_detector', last=True)

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
    global_notification = db.Column(db.Boolean, default=False) 

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

class Relevance(db.Model):
    __tablename__ = 'relevance'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    relevance_score = db.Column(db.Float, nullable=False)

TOPIC_TAGS = {
    'esportes': ['jogo', 'futebol', 'basquete', 'esportes', 'campeonato', 'brasileirão', 'fla'],
    'notícias': ['notícia', 'política', 'economia', 'brasil', 'mundo', 'governo', 'eleições'],
    'música': ['música', 'cantor', 'banda', 'álbum', 'show', 'festival'],
    'entretenimento': ['filme', 'cinema', 'série', 'ator', 'atriz', 'celebridade', 'tv'],
    'tecnologia': ['tecnologia', 'inovação', 'startup', 'software', 'hardware', 'ciência', 'teste', 'tags','algorítimo' ,'vaibes', 'disponível', 'próximo', 'atualização' ],
    'geek': ['geek', 'jogos', 'videogame', 'anime', 'hq', 'quadrinhos', 'mangá'],
    'cultura': ['cultura', 'arte', 'livro', 'dança', 'teatro', 'literatura', 'museu']
}