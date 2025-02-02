from flask import Blueprint, flash, render_template, request, session, redirect, url_for, jsonify
from app.models.models import User, Follower, Post
from app.utils.error_handler import handle_error
from app.extensions import db
from app.services.user_service import get_user_by_username

user_bp = Blueprint('users', __name__)

@user_bp.route('/<username>/profile')
def profile(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        flash('Usuário não encontrado.')
        return redirect(url_for('main.home'))
    posts = Post.query.filter_by(user_id=user.id).all()
    return render_template('profile.html', profile=user, user=user, posts=posts)

@user_bp.route('/follow_user/<username>', methods=['POST'])
def toggle_follow(username):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Obtém o usuário que deseja seguir usando o username
    user_to_follow = User.query.filter_by(username=username).first()
    current_user = User.query.get(session['user_id'])

    if user_to_follow and user_to_follow.id != current_user.id:
        # Verifica se já está seguindo
        existing_follow = Follower.query.filter_by(user_id=user_to_follow.id, follower_id=current_user.id).first()
        
        if existing_follow:
            # Deixar de seguir
            db.session.delete(existing_follow)
            db.session.commit()
            message = 'Você deixou de seguir este usuário.'
            following_status = False
        else:
            # Seguir
            new_follow = Follower(user_id=user_to_follow.id, follower_id=current_user.id)
            db.session.add(new_follow)
            db.session.commit()
            message = 'Você começou a seguir este usuário!'
            following_status = True
            
        return jsonify({'message': message, 'following': following_status}), 200

    return jsonify({'message': 'Erro ao processar a solicitação.'}), 400


@user_bp.route('/unfollow_user/<username>', methods=['POST'])
def unfollow_user(username):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_to_unfollow = get_user_by_username(username)
    user = User.query.get(session['user_id'])

    if user_to_unfollow:
        existing_follow = Follower.query.filter_by(user_id=user_to_unfollow.id, follower_id=user.id).first()
        if existing_follow:
            db.session.delete(existing_follow)
            db.session.commit()
            flash('Você deixou de seguir este usuário.', 'success')
        else:
            flash('Você não está seguindo este usuário.', 'warning')
    else:
        flash('Erro ao deixar de seguir o usuário.', 'danger')

    return redirect(url_for('profile', username=username))
