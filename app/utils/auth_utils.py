from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def requer_papel(*papeis_permitidos):
    """
    Decorador para proteger rotas com base no papel do usuário logado.
    Uso: @requer_papel("admin", "atendente")
    """
    def decorador(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            papel_atual = claims.get("papel")
            if papel_atual not in papeis_permitidos:
                return jsonify({
                    "erro": "Acesso negado: você não tem permissão para esta ação."
                }), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorador