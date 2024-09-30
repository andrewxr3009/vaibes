from app import app, db, User, Post, Follower
from flask import request, jsonify, redirect, url_for, session, flash, render_template

# Impementação de nova funcionalidade: Seguir usuários
@app.route('/follow/<int:user_id>', methods=['POST'])
def follow(user_id):
    if 'username' in session:
        current_user = User.query.filter_by(username=session['username']).first()
        if not current_user:
            return jsonify({'status': 'error', 'message': 'Usuário não encontrado.'}), 404

        user_to_follow = User.query.get(user_id)
        if not user_to_follow:
            return jsonify({'status': 'error', 'message': 'Usuário a seguir não encontrado.'}), 404

        # Verifica se já está seguindo
        follow_relation = Follower.query.filter_by(user_id=user_to_follow.id, follower_id=current_user.id).first()
        if follow_relation:
            flash('Você já segue este usuário.')
        else:
            new_follow = Follower(user_id=user_to_follow.id, follower_id=current_user.id)
            db.session.add(new_follow)
            db.session.commit()
            flash(f'Você agora segue {user_to_follow.username}!')

        return redirect(url_for('profile', username=current_user.username))
    else:
        return redirect(url_for('login'))

# Implementação de função de desfazer follow (opcional)
@app.route('/unfollow/<int:user_id>', methods=['POST'])
def unfollow(user_id):
    if 'username' in session:
        current_user = User.query.filter_by(username=session['username']).first()
        if not current_user:
            return jsonify({'status': 'error', 'message': 'Usuário não encontrado.'}), 404

        user_to_unfollow = User.query.get(user_id)
        if not user_to_unfollow:
            return jsonify({'status': 'error', 'message': 'Usuário a deixar de seguir não encontrado.'}), 404

        # Verifica se está seguindo
        follow_relation = Follower.query.filter_by(user_id=user_to_unfollow.id, follower_id=current_user.id).first()
        if follow_relation:
            db.session.delete(follow_relation)
            db.session.commit()
            flash(f'Você deixou de seguir {user_to_unfollow.username}.')
        else:
            flash('Você não está seguindo este usuário.')

        return redirect(url_for('profile', username=current_user.username))
    else:
        return redirect(url_for('login'))

# Nova rota para buscar seguidores
@app.route('/followers/<int:user_id>')
def followers(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('Usuário não encontrado.')
        return redirect(url_for('home'))
    
    followers = Follower.query.filter_by(user_id=user.id).all()
    return render_template('followers.html', user=user, followers=followers)

# Inicializando o aplicativo
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
