from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from app.extensions import db
from app.models import Chamado, Ocorrencia, User
from app.utils.auth_utils import requer_papel

chamado_bp = Blueprint("chamados", __name__, url_prefix="/api/chamados")
RAIO_AGREGACAO_METROS = 100.0


def _normalizar_servico(categoria):
    return categoria.strip().casefold()


def _distancia_em_metros(latitude_a, longitude_a, latitude_b, longitude_b):
    raio_terra_metros = 6_371_000
    diferenca_latitude = radians(latitude_b - latitude_a)
    diferenca_longitude = radians(longitude_b - longitude_a)
    componente = (
        sin(diferenca_latitude / 2) ** 2
        + cos(radians(latitude_a)) * cos(radians(latitude_b))
        * sin(diferenca_longitude / 2) ** 2
    )
    return 2 * raio_terra_metros * asin(sqrt(componente))


def _extrair_localizacao(dados):
    localizacao = dados.get("localizacao") or {}
    latitude = localizacao.get("latitude", dados.get("latitude"))
    longitude = localizacao.get("longitude", dados.get("longitude"))
    precisao_metros = localizacao.get("precisao_metros", dados.get("precisao_metros"))
    try:
        latitude = float(latitude)
        longitude = float(longitude)
        precisao_metros = float(precisao_metros) if precisao_metros is not None else None
    except (TypeError, ValueError):
        return None
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None
    if precisao_metros is not None and precisao_metros < 0:
        return None
    return latitude, longitude, precisao_metros


def _extrair_classificacao_geografica(dados):
    classificacao = dados.get("classificacao_geografica", "residencial")
    if not isinstance(classificacao, str):
        return None
    return classificacao.strip().casefold()


def _encontrar_ocorrencia_ativa(servico, latitude, longitude):
    candidatas = Ocorrencia.query.filter(
        Ocorrencia.servico == servico,
        Ocorrencia.status.in_(Ocorrencia.STATUS_ATIVOS),
    ).all()
    proximas = []
    for ocorrencia in candidatas:
        distancia = _distancia_em_metros(
            latitude, longitude, ocorrencia.latitude, ocorrencia.longitude
        )
        if distancia <= ocorrencia.raio_agregacao_metros:
            proximas.append((ocorrencia, distancia))
    return min(proximas, key=lambda item: item[1])[0] if proximas else None


@chamado_bp.post("")
@jwt_required()
def criar_chamado():
    dados = request.get_json(silent=True) or {}
    titulo = dados.get("titulo")
    descricao = dados.get("descricao")
    categoria = dados.get("categoria")
    prioridade = dados.get("prioridade", "media")
    if not titulo or not descricao or not categoria:
        return jsonify({"erro": "Campos obrigatórios: titulo, descricao, categoria."}), 400

    localizacao = _extrair_localizacao(dados)
    if localizacao is None:
        return jsonify({
            "erro": "Informe uma localização válida com latitude e longitude."
        }), 400
    classificacao_geografica = _extrair_classificacao_geografica(dados)
    if classificacao_geografica not in Ocorrencia.MULTIPLICADORES_GEO:
        return jsonify({
            "erro": "classificacao_geografica deve ser residencial, arterial ou sensivel."
        }), 400
    if prioridade not in Chamado.PRIORIDADES_VALIDAS:
        return jsonify({
            "erro": f"Prioridade inválida. Use uma de: {Chamado.PRIORIDADES_VALIDAS}"
        }), 400

    latitude, longitude, precisao_metros = localizacao
    ocorrencia = _encontrar_ocorrencia_ativa(
        _normalizar_servico(categoria), latitude, longitude
    )
    agregado = ocorrencia is not None
    if ocorrencia is None:
        ocorrencia = Ocorrencia(
            servico=_normalizar_servico(categoria),
            latitude=latitude,
            longitude=longitude,
            raio_agregacao_metros=RAIO_AGREGACAO_METROS,
            severidade_base=Ocorrencia.SEVERIDADES_POR_SERVICO.get(
                _normalizar_servico(categoria), Ocorrencia.SEVERIDADE_PADRAO
            ),
            classificacao_geografica=classificacao_geografica,
            multiplicador_geografico=Ocorrencia.MULTIPLICADORES_GEO[
                classificacao_geografica
            ],
        )
        db.session.add(ocorrencia)
    else:
        ocorrencia.atualizado_em = datetime.now(timezone.utc)

    chamado = Chamado(
        titulo=titulo, descricao=descricao, categoria=categoria, prioridade=prioridade,
        solicitante_id=int(get_jwt_identity()), ocorrencia=ocorrencia,
        latitude=latitude, longitude=longitude, precisao_metros=precisao_metros,
        localizacao_capturada_em=datetime.now(timezone.utc),
    )
    db.session.add(chamado)
    db.session.commit()
    return jsonify({
        "agregado": agregado,
        "chamado": chamado.to_dict(),
        "ocorrencia": ocorrencia.to_dict(),
    }), 201


@chamado_bp.get("")
@jwt_required()
def listar_chamados():
    papel_atual = get_jwt().get("papel")
    usuario_id = int(get_jwt_identity())
    query = Chamado.query
    if papel_atual == "usuario":
        query = query.filter_by(solicitante_id=usuario_id)
    status = request.args.get("status")
    prioridade = request.args.get("prioridade")
    if status:
        query = query.filter_by(status=status)
    if prioridade:
        query = query.filter_by(prioridade=prioridade)
    return jsonify([
        chamado.to_dict() for chamado in query.order_by(Chamado.criado_em.desc()).all()
    ]), 200


@chamado_bp.get("/<int:chamado_id>")
@jwt_required()
def obter_chamado(chamado_id):
    papel_atual = get_jwt().get("papel")
    usuario_id = int(get_jwt_identity())
    chamado = Chamado.query.get_or_404(chamado_id)
    if papel_atual == "usuario" and chamado.solicitante_id != usuario_id:
        return jsonify({"erro": "Acesso negado a este chamado."}), 403
    return jsonify(chamado.to_dict(incluir_comentarios=True)), 200


@chamado_bp.put("/<int:chamado_id>")
@jwt_required()
def atualizar_chamado(chamado_id):
    papel_atual = get_jwt().get("papel")
    usuario_id = int(get_jwt_identity())
    chamado = Chamado.query.get_or_404(chamado_id)
    dados = request.get_json(silent=True) or {}
    eh_dono = chamado.solicitante_id == usuario_id
    eh_staff = papel_atual in ("atendente", "admin")
    if not eh_dono and not eh_staff:
        return jsonify({"erro": "Acesso negado a este chamado."}), 403
    if eh_dono and not eh_staff:
        if chamado.status != "aberto":
            return jsonify({"erro": "Só é possível editar o chamado enquanto estiver aberto."}), 400
        chamado.titulo = dados.get("titulo", chamado.titulo)
        chamado.descricao = dados.get("descricao", chamado.descricao)
        chamado.categoria = dados.get("categoria", chamado.categoria)
    if eh_staff:
        status = dados.get("status")
        prioridade = dados.get("prioridade")
        responsavel_id = dados.get("responsavel_id")
        if status is not None:
            if status not in Chamado.STATUS_VALIDOS:
                return jsonify({"erro": f"Status inválido. Use um de: {Chamado.STATUS_VALIDOS}"}), 400
            chamado.status = status
        if prioridade is not None:
            if prioridade not in Chamado.PRIORIDADES_VALIDAS:
                return jsonify({"erro": f"Prioridade inválida. Use uma de: {Chamado.PRIORIDADES_VALIDAS}"}), 400
            chamado.prioridade = prioridade
        if responsavel_id is not None:
            responsavel = User.query.get(responsavel_id)
            if not responsavel or responsavel.papel not in ("atendente", "admin"):
                return jsonify({"erro": "responsavel_id deve ser de um usuário atendente ou admin."}), 400
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
