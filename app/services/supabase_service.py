from app.extensions import supabase_client, firebase_bucket
import uuid
from datetime import datetime

def create_post_service(user_id, content, image_url=None):
    """
    Cria um post no Supabase.
    """
    post_id = str(uuid.uuid4())
    post_data = {
        "id": post_id,
        "user_id": user_id,
        "content": content,
        "image_url": image_url,
        "timestamp": datetime.utcnow().isoformat(),
        "likes": 0,
    }

    response = supabase_client.table('posts').insert(post_data).execute()
    if response.error:
        raise ValueError(f"Erro ao criar post: {response.error}")
    return post_id

def upload_image_to_firebase(image):
    """
    Faz upload de uma imagem para o Firebase Storage.
    """
    blob = firebase_bucket.blob(f"posts/{uuid.uuid4()}.jpg")
    blob.upload_from_file(image, content_type=image.content_type)
    blob.make_public()  # Torna a imagem pública
    return blob.public_url

def add_comment_service(post_id, user_id, content):
    """
    Adiciona um comentário a um post no Supabase.
    """
    comment_id = str(uuid.uuid4())
    comment_data = {
        "id": comment_id,
        "post_id": post_id,
        "user_id": user_id,
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
    }

    response = supabase_client.table('comments').insert(comment_data).execute()
    if response.error:
        raise ValueError(f"Erro ao adicionar comentário: {response.error}")
    return comment_id
