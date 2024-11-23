from .main_routes import main_bp
from .post_routes import post_bp
from .user_routes import user_bp
from .auth_routes import auth_bp
from .notification_routes import notification_bp
from .hashtag_routes import hashtag_bp

def register_routes(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(post_bp, url_prefix='/posts')
    app.register_blueprint(user_bp, url_prefix='/users')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(notification_bp, url_prefix='/notifications')
    app.register_blueprint(hashtag_bp, url_prefix='/hashtags')
