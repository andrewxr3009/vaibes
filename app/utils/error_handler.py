import logging
import traceback
from flask import jsonify

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def handle_error(e):
    error_type = type(e).__name__  # Tipo do erro (ex: KeyError, ValueError)
    error_message = str(e)  # Mensagem do erro
    error_traceback = traceback.format_exc()  # Traceback completo do erro

    # Log detalhado do erro
    logger.error("Ocorreu um erro.")
    logger.error(f"Tipo do erro: {error_type}")
    logger.error(f"Mensagem: {error_message}")
    logger.error("Traceback completo:")
    logger.error(error_traceback)

    # Retorno mais informativo para o cliente (opcionalmente limitado em produção)
    return jsonify({
        "error": "Ocorreu um erro interno no servidor.",
        "details": {
            "type": error_type,
            "message": error_message
        }
    }), 500
