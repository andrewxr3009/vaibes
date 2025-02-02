from app.extensions import supabase_client, firebase_bucket
import uuid
from datetime import datetime
from pytz import timezone

def horario_atual_brasilia():
    fuso_brasilia = timezone('America/Sao_Paulo')
    return datetime.now(fuso_brasilia)

def create_post_service(user_id, content, image_url=None, gif_url=None):
    """
    Cria um post no Supabase usando ID incremental.
    """
    # Consulta o último ID na tabela 'post'
    last_response = supabase_client.table('post')\
                        .select('id')\
                        .order('id', desc=True)\
                        .limit(1)\
                        .execute()

    if last_response.data and len(last_response.data) > 0:
        try:
            last_id = int(last_response.data[0]['id'])
        except (ValueError, TypeError):
            last_id = 0
    else:
        last_id = 0

    # Incrementa o último ID em 1
    new_id = last_id + 1

    post_data = {
        "id": new_id,
        "user_id": user_id,
        "content": content,
        "img_url": image_url,
        "gif_url": gif_url,  # Pode ser None se não informado
        "timestamp": horario_atual_brasilia().isoformat(),
    }

    response = supabase_client.table('post').insert(post_data).execute()
    response_dict = response.dict()  # Converte a resposta para dicionário
    if response_dict.get("error"):
        raise ValueError(f"Erro ao criar post: {response_dict.get('error')}")
    return new_id

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
