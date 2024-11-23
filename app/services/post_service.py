from flask import url_for
from app.models.models import Post
from app.extensions import db, redis_client
from app.models.models import Post, Hashtag, PostHashtag, Relevance
from app.extensions import db
from datetime import datetime
from app.extensions import supabase_client, firebase_bucket
import uuid
from datetime import datetime

def get_paginated_posts(user_id, page=1, per_page=10, filter_type='relevance'):
    """
    Retorna os posts paginados com base no tipo de filtro.
    """
    if filter_type == 'relevance':
        # Busca os posts relevantes ao usuário
        relevant_posts = (
            db.session.query(Post)
            .join(Relevance, Relevance.post_id == Post.id)
            .filter(Relevance.user_id == user_id)
            .order_by(Relevance.relevance_score.desc())
            .paginate(page=page, per_page=per_page)
        )
        return {
            'posts': [serialize_post(post) for post in relevant_posts.items],
            'has_more': relevant_posts.has_next
        }
    elif filter_type == 'chronological':
        # Busca os posts mais recentes em ordem cronológica
        paginated_posts = (
            Post.query
            .order_by(Post.timestamp.desc())
            .paginate(page=page, per_page=per_page)
        )
        return {
            'posts': [serialize_post(post) for post in paginated_posts.items],
            'has_more': paginated_posts.has_next
        }
    else:
        raise ValueError("Tipo de filtro inválido.")

def serialize_post(post):
    """
    Serializa um post para formato JSON.
    """
    return {
        "id": post.id,
        "content": post.content,
        "timestamp": post.timestamp.isoformat(),
        "likes": len(post.likes),
        "gif_url": post.gif_url,
        "img_url": post.img_url,
        "user": {
            "id": post.user.id,  # Acessando o 'User' pelo relacionamento
            "username": post.user.username,  # Acessando diretamente o 'username'
            "profile_picture": post.user.profile_picture or url_for('static', filename='uploads/default-profile-pic.png')  # Acessando a foto de perfil
        }
    }



def create_post_service(user_id, content, image_url=None, gif_url=None):
    """
    Cria um post no Supabase.
    """
    post_id = str(uuid.uuid4())
    post_data = {
        "id": post_id,
        "user_id": user_id,
        "content": content,
        "image_url": image_url,  # URL da imagem (se aplicável)
        "gif_url": gif_url,      # URL do GIF (se aplicável)
        "timestamp": datetime.utcnow().isoformat(),
        "likes": 0,
    }

    response = supabase_client.table('posts').insert(post_data).execute()
    if response.error:
        raise ValueError(f"Erro ao criar post: {response.error}")
    return post_id
