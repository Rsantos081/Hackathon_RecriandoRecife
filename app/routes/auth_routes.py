from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/registrar")
def registrar():
    dados = request.get_json(silent=True) or {}

    nome = dados.get("nome")
    email = dados.get("email")
    senha = dados.get("senha")
    papel = dados.get("papel", "usuario")

    if not nome or not email or not senha:
        return jsonify({"erro": "Campos obrigatórios: nome, email, senha."}), 400

    if papel not in User.ROLES:
        return jsonify({"erro": f"Papel inválido. Use um de: {User.ROLES}"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"erro": "Já existe um usuário com este e-mail."}), 409

    usuario = User(nome=nome, email=email, papel=papel)
    usuario.set_senha(senha)

    db.session.add(usuario)
    db.session.commit()

    return jsonify(usuario.to_dict()), 201


@auth_bp.post("/login")
def login():
    dados = request.get_json(silent=True) or {}
    email = dados.get("email")
    senha = dados.get("senha")

    if not email or not senha:
        return jsonify({"erro": "Informe email e senha."}), 400

    usuario = User.query.filter_by(email=email).first()

    if not usuario or not usuario.checar_senha(senha):
        return jsonify({"erro": "Credenciais inválidas."}), 401

    token = create_access_token(
        identity=str(usuario.id),
        additional_claims={"papel": usuario.papel, "nome": usuario.nome},
    )

    return jsonify({
        "access_token": token,
        "usuario": usuario.to_dict(),
    }), 200