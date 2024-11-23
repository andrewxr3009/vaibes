from flask import Blueprint, jsonify, request
from app.models.models import Hashtag, PostHashtag
from app.utils.error_handler import handle_error

hashtag_bp = Blueprint('hashtags', __name__)

@hashtag_bp.route('/hashtag/<string:name>')
def view_hashtag(name):
    try:
        hashtag = Hashtag.query.filter_by(name=name).first()
        if not hashtag:
            return jsonify({"message": "Hashtag não encontrada"}), 404
        posts = PostHashtag.query.filter_by(hashtag_id=hashtag.id).all()
        return jsonify(posts=[p.post_id for p in posts])
    except Exception as e:
        return handle_error(e)
