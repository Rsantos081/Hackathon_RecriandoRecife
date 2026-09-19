from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

from app.extensions import db
from app.models import Chamado, User
from app.utils.auth_utils import requer_papel

chamado_bp = Blueprint("chamados", __name__, url_prefix="/api/chamados")


@chamado_bp.post("")
@jwt_required()
def criar_chamado():
    dados = request.get_json(silent=True) or {}
    titulo = dados.get("titulo")
    descricao = dados.get("descricao")
    categoria = dados.get("categoria")
    prioridade = dados.get("prioridade", "media")

    if not titulo or not descricao:
        return jsonify({"erro": "Campos obrigatórios: titulo, descricao."}), 400

    if prioridade not in Chamado.PRIORIDADES_VALIDAS:
        return jsonify({
            "erro": f"Prioridade inválida. Use uma de: {Chamado.PRIORIDADES_VALIDAS}"
        }), 400

    solicitante_id = int(get_jwt_identity())

    chamado = Chamado(
        titulo=titulo,
        descricao=descricao,
        categoria=categoria,
        prioridade=prioridade,
        solicitante_id=solicitante_id,
    )
    db.session.add(chamado)
    db.session.commit()

    return jsonify(chamado.to_dict()), 201


@chamado_bp.get("")
@jwt_required()
def listar_chamados():
    claims = get_jwt()
    papel_atual = claims.get("papel")
    usuario_id = int(get_jwt_identity())

    query = Chamado.query

    # Usuário comum só vê os próprios chamados; atendente/admin veem todos
    if papel_atual == "usuario":
        query = query.filter_by(solicitante_id=usuario_id)

    # Filtros opcionais via query string
    status = request.args.get("status")
    prioridade = request.args.get("prioridade")
    if status:
        query = query.filter_by(status=status)
    if prioridade:
        query = query.filter_by(prioridade=prioridade)

    chamados = query.order_by(Chamado.criado_em.desc()).all()
    return jsonify([c.to_dict() for c in chamados]), 200


@chamado_bp.get("/<int:chamado_id>")
@jwt_required()
def obter_chamado(chamado_id):
    claims = get_jwt()
    papel_atual = claims.get("papel")
    usuario_id = int(get_jwt_identity())

    chamado = Chamado.query.get_or_404(chamado_id)

    if papel_atual == "usuario" and chamado.solicitante_id != usuario_id:
        return jsonify({"erro": "Acesso negado a este chamado."}), 403

    return jsonify(chamado.to_dict(incluir_comentarios=True)), 200


@chamado_bp.put("/<int:chamado_id>")
@jwt_required()
def atualizar_chamado(chamado_id):
    claims = get_jwt()
    papel_atual = claims.get("papel")
    usuario_id = int(get_jwt_identity())

    chamado = Chamado.query.get_or_404(chamado_id)
    dados = request.get_json(silent=True) or {}

    eh_dono = chamado.solicitante_id == usuario_id
    eh_staff = papel_atual in ("atendente", "admin")

    if not eh_dono and not eh_staff:
        return jsonify({"erro": "Acesso negado a este chamado."}), 403

    # Usuário comum (dono) só pode editar título/descrição enquanto estiver aberto
    if eh_dono and not eh_staff:
        if chamado.status != "aberto":
            return jsonify({
                "erro": "Só é possível editar o chamado enquanto o status for 'aberto'."
            }), 400
        chamado.titulo = dados.get("titulo", chamado.titulo)
        chamado.descricao = dados.get("descricao", chamado.descricao)
        chamado.categoria = dados.get("categoria", chamado.categoria)

    # Atendente/admin podem alterar status, prioridade e responsável
    if eh_staff:
        status = dados.get("status")
        prioridade = dados.get("prioridade")
        responsavel_id = dados.get("responsavel_id")

        if status is not None:
            if status not in Chamado.STATUS_VALIDOS:
                return jsonify({
                    "erro": f"Status inválido. Use um de: {Chamado.STATUS_VALIDOS}"
                }), 400
            chamado.status = status

        if prioridade is not None:
            if prioridade not in Chamado.PRIORIDADES_VALIDAS:
                return jsonify({
                    "erro": f"Prioridade inválida. Use uma de: {Chamado.PRIORIDADES_VALIDAS}"
                }), 400
            chamado.prioridade = prioridade

        if responsavel_id is not None:
            responsavel = User.query.get(responsavel_id)
            if not responsavel or responsavel.papel not in ("atendente", "admin"):
                return jsonify({
                    "erro": "responsavel_id deve ser de um usuário atendente ou admin."
                }), 400
            chamado.responsavel_id = responsavel_id

        chamado.titulo = dados.get("titulo", chamado.titulo)
        chamado.descricao = dados.get("descricao", chamado.descricao)
        chamado.categoria = dados.get("categoria", chamado.categoria)

    db.session.commit()
    return jsonify(chamado.to_dict()), 200


@chamado_bp.delete("/<int:chamado_id>")
@requer_papel("admin")
def deletar_chamado(chamado_id):
    chamado = Chamado.query.get_or_404(chamado_id)
    db.session.delete(chamado)
    db.session.commit()
    return jsonify({"mensagem": "Chamado excluído com sucesso."}), 200