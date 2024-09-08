def share_post(post_id, user):
    from app import db, Post, Share  # Importando dentro da função para evitar importação circular
    post = Post.query.get(post_id)
    if post:
        new_share = Share(post_id=post.id, user_id=user.id)
        db.session.add(new_share)
        db.session.commit()
        return {'status': 'success', 'message': 'Post compartilhado com sucesso!'}
    return {'status': 'error', 'message': 'Post não encontrado.'}

def like_post(post_id, user):
    from app import db, Post, Like  # Importando dentro da função
    post = Post.query.get(post_id)
    
    if post:
        # Verifica se o usuário já curtiu o post
        existing_like = Like.query.filter_by(post_id=post.id, user_id=user.id).first()
        
        if existing_like:
            return {'status': 'error', 'message': 'Você já curtiu este post.'}
        
        # Adiciona a curtida
        new_like = Like(post_id=post.id, user_id=user.id)
        db.session.add(new_like)
        db.session.commit()
        
        return {'status': 'success', 'message': 'Post curtido!'}
    
    return {'status': 'error', 'message': 'Post não encontrado.'}
def comment_post(post_id, user, content):
    from app import db, Post, Comment  # Importando dentro da função
    post = Post.query.get(post_id)
    if post and content:
        new_comment = Comment(post_id=post.id, user_id=user.id, content=content)
        db.session.add(new_comment)
        db.session.commit()
        return {'status': 'success', 'message': 'Comentário adicionado!'}
    return {'status': 'error', 'message': 'Erro ao adicionar comentário.'}
