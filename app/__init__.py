from flask import Flask, jsonify
from sqlalchemy import inspect, text

from config import Config
from app.extensions import db, jwt


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    jwt.init_app(app)

    from app.routes.auth_routes import auth_bp
    from app.routes.chamado_routes import chamado_bp
    from app.routes.comentario_routes import comentario_bp
    from app.routes.ocorrencia_routes import ocorrencia_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(chamado_bp)
    app.register_blueprint(comentario_bp)
    app.register_blueprint(ocorrencia_bp)

    @app.get("/api/saude")
    def saude():
        return jsonify({"status": "ok", "servico": "API de Chamados"}), 200

    @app.errorhandler(404)
    def nao_encontrado(erro):
        return jsonify({"erro": "Recurso não encontrado."}), 404

    @app.errorhandler(405)
    def metodo_nao_permitido(erro):
        return jsonify({"erro": "Método não permitido para esta rota."}), 405

    @app.errorhandler(500)
    def erro_interno(erro):
        db.session.rollback()
        return jsonify({"erro": "Erro interno do servidor."}), 500

    with app.app_context():
        db.create_all()
        colunas_chamados = {
            coluna["name"] for coluna in inspect(db.engine).get_columns("chamados")
        }
        novas_colunas = {
            "ocorrencia_id": "INTEGER REFERENCES ocorrencias(id)",
            "latitude": "FLOAT",
            "longitude": "FLOAT",
            "precisao_metros": "FLOAT",
            "localizacao_capturada_em": "DATETIME",
        }
        for nome, definicao in novas_colunas.items():
            if nome not in colunas_chamados:
                db.session.execute(text(
                    f"ALTER TABLE chamados ADD COLUMN {nome} {definicao}"
                ))
        colunas_ocorrencias = {
            coluna["name"] for coluna in inspect(db.engine).get_columns("ocorrencias")
        }
        novas_colunas_ocorrencias = {
            "severidade_base": "FLOAT NOT NULL DEFAULT 3.0",
            "classificacao_geografica": "VARCHAR(20) NOT NULL DEFAULT 'residencial'",
            "multiplicador_geografico": "FLOAT NOT NULL DEFAULT 1.0",
        }
        for nome, definicao in novas_colunas_ocorrencias.items():
            if nome not in colunas_ocorrencias:
                db.session.execute(text(
                    f"ALTER TABLE ocorrencias ADD COLUMN {nome} {definicao}"
                ))
        db.session.commit()

    return app
