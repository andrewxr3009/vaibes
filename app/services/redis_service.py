from app.extensions import redis_client

def like_post_service(user_id, post_id):
    """
    Adiciona um like a um post no Redis.
    """
    key = f"likes:post:{post_id}"
    result = redis_client.sadd(key, user_id)  # Adiciona o usuário ao set
    return result == 1  # Retorna True se o like foi registrado, False se já existia

def get_likes_count(post_id):
    """
    Retorna a contagem de likes de um post.
    """
    key = f"likes:post:{post_id}"
    return redis_client.scard(key)  # Conta o número de elementos no set
