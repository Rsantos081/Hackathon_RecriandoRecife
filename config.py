import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Chave secreta usada para assinar sessões/tokens diversos
    SECRET_KEY = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")

    # Banco de dados (SQLite por padrão; troque a URI para usar Postgres/MySQL)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'chamados.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "troque-esta-chave-jwt-tambem")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)