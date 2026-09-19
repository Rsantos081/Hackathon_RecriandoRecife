from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

from app.extensions import db
from app.models import Chamado, Comentario

comentario_bp = Blueprint("comentarios", __name__, url_prefix="/api/chamados")


def _pode_acessar_chamado(chamado, papel_atual, usuario_id):
    if papel_atual == "usuario" and chamado.solicitante_id != usuario_id:
        return False
    return True


@comentario_bp.post("/<int:chamado_id>/comentarios")
@jwt_required()
def adicionar_comentario(chamado_id):
    claims = get_jwt()
    papel_atual = claims.get("papel")
    usuario_id = int(get_jwt_identity())

    chamado = Chamado.query.get_or_404(chamado_id)

    if not _pode_acessar_chamado(chamado, papel_atual, usuario_id):
        return jsonify({"erro": "Acesso negado a este chamado."}), 403

    dados = request.get_json(silent=True) or {}
    texto = dados.get("texto")

    if not texto:
        return jsonify({"erro": "Campo obrigatório: texto."}), 400

    comentario = Comentario(texto=texto, autor_id=usuario_id, chamado_id=chamado.id)
    db.session.add(comentario)
    db.session.commit()

    return jsonify(comentario.to_dict()), 201


@comentario_bp.get("/<int:chamado_id>/comentarios")
@jwt_required()
def listar_comentarios(chamado_id):
    claims = get_jwt()
    papel_atual = claims.get("papel")
    usuario_id = int(get_jwt_identity())

    chamado = Chamado.query.get_or_404(chamado_id)

    if not _pode_acessar_chamado(chamado, papel_atual, usuario_id):
        return jsonify({"erro": "Acesso negado a este chamado."}), 403

    return jsonify([c.to_dict() for c in chamado.comentarios]), 200