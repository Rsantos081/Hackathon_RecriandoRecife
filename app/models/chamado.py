from datetime import datetime, timezone

from app.extensions import db


class Chamado(db.Model):
    __tablename__ = "chamados"

    STATUS_VALIDOS = ("aberto", "em_andamento", "resolvido", "fechado")
    PRIORIDADES_VALIDAS = ("baixa", "media", "alta", "urgente")

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(80), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="aberto")
    prioridade = db.Column(db.String(20), nullable=False, default="media")

    solicitante_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    responsavel_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    ocorrencia_id = db.Column(db.Integer, db.ForeignKey("ocorrencias.id"), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    precisao_metros = db.Column(db.Float, nullable=True)
    localizacao_capturada_em = db.Column(db.DateTime, nullable=True)

    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    atualizado_em = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    solicitante = db.relationship(
        "User", back_populates="chamados_abertos", foreign_keys=[solicitante_id]
    )
    responsavel = db.relationship(
        "User", back_populates="chamados_responsavel", foreign_keys=[responsavel_id]
    )
    ocorrencia = db.relationship("Ocorrencia", back_populates="chamados")
    comentarios = db.relationship(
        "Comentario", back_populates="chamado",
        cascade="all, delete-orphan", order_by="Comentario.criado_em"
    )

    def to_dict(self, incluir_comentarios=False):
        data = {
            "id": self.id,
            "titulo": self.titulo,
            "descricao": self.descricao,
            "categoria": self.categoria,
            "status": self.status,
            "prioridade": self.prioridade,
            "ocorrencia_id": self.ocorrencia_id,
            "localizacao": (
                {
                    "latitude": self.latitude,
                    "longitude": self.longitude,
                    "precisao_metros": self.precisao_metros,
                    "capturada_em": (
                        self.localizacao_capturada_em.isoformat()
                        if self.localizacao_capturada_em
                        else None
                    ),
                }
                if self.latitude is not None and self.longitude is not None
                else None
            ),
            "solicitante": self.solicitante.to_dict() if self.solicitante else None,
            "responsavel": self.responsavel.to_dict() if self.responsavel else None,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }
        if incluir_comentarios:
            data["comentarios"] = [c.to_dict() for c in self.comentarios]
        return data
