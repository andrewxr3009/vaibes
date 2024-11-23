from flask import Blueprint, request, jsonify, session, redirect, url_for, flash, render_template
from app.models.models import Post, Notification, User, Hashtag, Like
from app.services.supabase_service import create_post_service, upload_image_to_firebase
from app.services.redis_service import like_post_service, get_likes_count 
from app.utils.error_handler import handle_error
from app.extensions import db

post_bp = Blueprint('posts', __name__)

@post_bp.route('/create', methods=['POST'])
def create_post():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Usuário não autenticado."}), 401

        content = request.form.get('content')
        gif_url = request.form.get('gif_url')  # URL do GIF opcional
        image = request.files.get('image')    # Imagem opcional

        if not content and not gif_url and not image:
            return jsonify({"error": "O post deve conter texto, GIF ou imagem."}), 400

        # Upload da imagem para o Firebase Storage, se houver
        image_url = None
        if image:
            image_url = upload_image_to_firebase(image)

        # Cria o post no Supabase
        post_id = create_post_service(user_id, content, image_url, gif_url)

        return jsonify({"message": "Post criado com sucesso!", "post_id": post_id}), 201
    except Exception as e:
        return handle_error(e)


@post_bp.route('/<int:post_id>', methods=['GET'])
def post_detail(post_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    try:
        post = Post.query.get(post_id)
        if not post:
            flash('Post não encontrado.', 'danger')
            return redirect(url_for('main.home'))
        return render_template('post_detail.html', post=post)
    except Exception as e:
        return handle_error(e)
    
@post_bp.route('/like_post/<int:post_id>', methods=['POST'])
def like_post(post_id):
    user_id = session.get('user_id')  # Recupera o usuário atual da sessão
    if not user_id:
        return jsonify({'error': 'Usuário não autenticado'}), 403

    post = Post.query.get(post_id)
    if not post:
        return jsonify({'error': 'Post não encontrado'}), 404

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404

    # Verifica se o usuário já curtiu o post
    like = Like.query.filter_by(post_id=post_id, user_id=user_id).first()
    
    if like:
        # Se o usuário já curtiu, descurte (remove o like)
        db.session.delete(like)
        db.session.commit()
        return jsonify({'likes': len(post.likes), 'liked': False})

    else:
        # Se o usuário não curtiu, adiciona o like
        new_like = Like(post_id=post_id, user_id=user_id)
        db.session.add(new_like)
        db.session.commit()
        return jsonify({'likes': len(post.likes), 'liked': True})
    

def user_likes_post(user_id, post_id):
    """Verifica se o usuário já curtiu o post."""
    like = Like.query.filter_by(user_id=user_id, post_id=post_id).first()
    return like is not None  #
