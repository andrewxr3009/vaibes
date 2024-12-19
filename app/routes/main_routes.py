from flask import Blueprint, session, redirect, url_for, request, render_template, flash, jsonify, send_from_directory
from app.models.models import User, Post, Comment, Hashtag
from app.services.post_service import get_paginated_posts
from app.routes.post_routes import user_likes_post
from app.utils.error_handler import handle_error
from app.extensions import db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    user_id = session.get('user_id')  # Use 'user_id' para pegar o ID do usuário da sessão
    
    if user_id is None:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)  # Obtém o usuário do banco de dados com o ID da sessão
    if not user:
        flash('Usuário não encontrado.')
        return redirect(url_for('auth.logout'))

    filter_type = request.args.get('filter', 'relevance')
    page = request.args.get('page', 1, type=int)

    try:
        paginated_data = get_paginated_posts(user.id, page, 10, filter_type)
        
        # Passa a chave 'liked' para cada post
        for post in paginated_data['posts']:
            post['liked'] = user_likes_post(user.id, post['id'])  # Verifica se o usuário curtiu o post

        return render_template('home.html', posts=paginated_data['posts'], has_more=paginated_data['has_more'], user=user)
    
    except Exception as e:
        return handle_error(e)

    


@main_bp.route('/load_posts', methods=['GET'])
def load_posts():
    page = request.args.get('page', 1, type=int)
    filter_type = request.args.get('filter', 'relevance')
    posts_per_page = 10

    # Lógica de filtro para 'relevance' ou 'chronological'
    if filter_type == 'relevance':
        posts = Post.query.order_by(Post.relevance_score.desc()).paginate(page=page, per_page=posts_per_page)
    else:
        posts = Post.query.order_by(Post.timestamp.desc()).paginate(page=page, per_page=posts_per_page)

    # Converter posts em uma lista com os dados necessários
    posts_with_users = [
        {
            "id": post.id,
            "content": post.content,
            "timestamp": post.timestamp.isoformat(),
            "likes": len(post.likes),
            "gif_url": post.gif_url,
            "img_url": post.img_url,
            "user": {
                "id": post.user_id.id,
                "username": post.user_id.username,
                "profile_picture": post.user_id.profile_picture
            }
        }
        for post in posts.items
    ]

    # Retornar dados em formato JSON
    return print(posts_with_users), jsonify({
        'posts': posts_with_users,
        'has_more': posts.has_next
    })

    
@main_bp.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')  # Pega a query de pesquisa da URL
    filter_type = request.args.get('filter', 'all')  # Pega o filtro de pesquisa (todos, pessoas, posts, hashtags, etc.)

    # Se a query estiver vazia, redireciona para a página inicial
    if not query:
        return redirect(url_for('main.home'))

    results = []

    # Processa a pesquisa com base no filtro
    if filter_type == 'all':
        # Pesquisa em todos os tipos (posts, pessoas, hashtags)
        posts = Post.query.filter(Post.content.ilike(f'%{query}%')).all()
        users = User.query.filter(User.username.ilike(f'%{query}%')).all()
        hashtags = Hashtag.query.filter(Hashtag.name.ilike(f'%{query}%')).all()
        results = {'posts': posts, 'users': users, 'hashtags': hashtags}
    elif filter_type == 'people':
        # Pesquisa apenas por pessoas (usuários)
        results = {'users': User.query.filter(User.username.ilike(f'%{query}%')).all()}
    elif filter_type == 'posts':
        # Pesquisa apenas por posts
        results = {'posts': Post.query.filter(Post.content.ilike(f'%{query}%')).all()}
    elif filter_type == 'hashtags':
        # Pesquisa apenas por hashtags
        results = {'hashtags': Hashtag.query.filter(Hashtag.name.ilike(f'%{query}%')).all()}

    # Renderiza a página de resultados de pesquisa
    return render_template('search.html', query=query, results=results)



@main_bp.route('/select_interests', methods=['GET', 'POST'])
def select_interests():
    if request.method == 'POST':
        selected_interests = request.form.getlist('interests')
        user = User.query.get(session.get('user_id'))
        user.interests = '{' + ','.join(selected_interests) + '}'
        db.session.commit()
        flash('Interesses salvos com sucesso!')
        return redirect(url_for('main.home'))
    return render_template('interest.html')


@main_bp.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if 'user_id' not in session or session['user_id'] != 18:
        flash("Acesso negado.", "danger")
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        post_id = request.form.get('post_id')
        if post_id:
            Post.query.filter_by(id=post_id).delete()
            db.session.commit()
            flash(f"Post {post_id} excluído com sucesso!", "success")

    users = User.query.all()
    posts = Post.query.all()
    return render_template('admin.html', users=users, posts=posts)

@app.route('/google6242ed33947064b2.html')
def serve_verification_file():
    return send_from_directory('static', 'google6242ed33947064b2.html')


