from flask import Blueprint, session, jsonify
from app.models.models import Notification
from app.utils.error_handler import handle_error

notification_bp = Blueprint('notifications', __name__)

@notification_bp.route('/notifications')
def notifications():
    try:
        user_id = session.get('user_id')
        notifications = Notification.query.filter_by(user_id=user_id).all()
        return jsonify([n.message for n in notifications])
    except Exception as e:
        return handle_error(e)
