from flask import Blueprint, request, jsonify, session
from app.utils.error_handler import handle_error
from app.services.supabase_service import add_comment_service

comment_bp = Blueprint('comments', __name__)

@comment_bp.route('/comment/<post_id>', methods=['POST'])
def add_comment(post_id):
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Usuário não autenticado."}), 401

        content = request.json.get('content')
        if not content:
            return jsonify({"error": "O comentário não pode estar vazio."}), 400

        comment_id = add_comment_service(post_id, user_id, content)
        return jsonify({"message": "Comentário adicionado com sucesso!", "comment_id": comment_id}), 201
    except Exception as e:
        return handle_error(e)
