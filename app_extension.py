from flask import Flask, request, jsonify, redirect, url_for, session, flash, render_template
from flask_socketio import SocketIO, emit
from app import app, db, User, Post, Follower
from vaibes_algorithm import calculate_relevance_for_all_users, schedule_relevance_calculation, session

# Inicialização do SocketIO
socketio = SocketIO(app)

# Implementação de nova funcionalidade: Seguir usuários
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

# Rota para executar o algoritmo de relevância
@app.route('/algorithm', methods=['GET'])
def algorithm():
    try:
        calculate_relevance_for_all_users(session)
        return "Algoritmo de relevância executado com sucesso!", 200
    except Exception as e:
        return f"Ocorreu um erro: {e}", 500
from apscheduler.schedulers.background import BackgroundScheduler

def run_algorithm():
    try:
        calculate_relevance_for_all_users(session)
    except Exception as e:
        print(f"Ocorreu um erro ao executar o algoritmo: {e}")

if __name__ == '__main__':
    # Cria e inicia o scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_algorithm, 'interval', seconds=240)  # Executa a cada 60 segundos
    scheduler.start()

    # Inicia o servidor Flask
    socketio.run(app, debug=True)
