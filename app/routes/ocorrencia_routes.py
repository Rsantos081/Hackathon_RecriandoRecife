from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from app.models import Ocorrencia

ocorrencia_bp = Blueprint("ocorrencias", __name__, url_prefix="/api/ocorrencias")


@ocorrencia_bp.get("")
@jwt_required()
def listar_ocorrencias():
    papel_atual = get_jwt().get("papel")
    usuario_id = int(get_jwt_identity())
    query = Ocorrencia.query
    if papel_atual == "usuario":
        query = (
            query.join(Ocorrencia.chamados)
            .filter_by(solicitante_id=usuario_id)
            .distinct()
        )
    ocorrencias = sorted(
        query.all(),
        key=lambda ocorrencia: (
            ocorrencia.score_criticidade,
            ocorrencia.atualizado_em,
        ),
        reverse=True,
    )
    return jsonify([
        ocorrencia.to_dict(incluir_chamados=papel_atual in ("atendente", "admin"))
        for ocorrencia in ocorrencias
    ]), 200
