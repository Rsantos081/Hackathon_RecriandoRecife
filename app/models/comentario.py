from datetime import datetime, timezone

from app.extensions import db


class Comentario(db.Model):
    __tablename__ = "comentarios"

    id = db.Column(db.Integer, primary_key=True)
    texto = db.Column(db.Text, nullable=False)
    autor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    chamado_id = db.Column(db.Integer, db.ForeignKey("chamados.id"), nullable=False)
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    autor = db.relationship("User")
    chamado = db.relationship("Chamado", back_populates="comentarios")

    def to_dict(self):
        return {
            "id": self.id,
            "texto": self.texto,
            "autor": self.autor.to_dict() if self.autor else None,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }