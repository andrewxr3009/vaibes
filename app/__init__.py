from flask import Flask
from .config import Config
from .extensions import db, redis_client, cors, socketio
from .routes import register_routes
from datetime import datetime


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializa extensões
    db.init_app(app)
    cors.init_app(app)
    socketio.init_app(app)

    # Registra rotas
    register_routes(app)

    # Cria o banco de dados, se necessário
    with app.app_context():
        db.create_all()

    @app.template_filter('format_datetime')
    def format_datetime(value):
        if value:
            # Verifica se o valor já é um objeto datetime, se não, tenta convertê-lo
            if isinstance(value, str):
                value = datetime.fromisoformat(value)  # Converte a string para datetime se for necessário
            return value.strftime('%d de %B de %Y %H:%M')  # Formato: 20 de outubro de 2024 16:44
        return value

    



    return app
