from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    ROLES = ("usuario", "atendente", "admin")

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    papel = db.Column(db.String(20), nullable=False, default="usuario")
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    chamados_abertos = db.relationship(
        "Chamado", back_populates="solicitante",
        foreign_keys="Chamado.solicitante_id"
    )
    chamados_responsavel = db.relationship(
        "Chamado", back_populates="responsavel",
        foreign_keys="Chamado.responsavel_id"
    )

    def set_senha(self, senha_plana):
        self.senha_hash = generate_password_hash(senha_plana)

    def checar_senha(self, senha_plana):
        return check_password_hash(self.senha_hash, senha_plana)

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "email": self.email,
            "papel": self.papel,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }