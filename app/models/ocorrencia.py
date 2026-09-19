from datetime import datetime, timezone
from math import log

from app.extensions import db


class Ocorrencia(db.Model):
    __tablename__ = "ocorrencias"

    STATUS_ATIVOS = ("aberta", "em_atendimento")
    STATUS_VALIDOS = (*STATUS_ATIVOS, "resolvida", "fechada")
    ALFA_MOBILIZACAO = 0.8
    BETA_ENVELHECIMENTO_POR_HORA = 0.05
    MULTIPLICADORES_GEO = {
        "residencial": 1.0,
        "arterial": 1.4,
        "sensivel": 1.8,
    }
    SEVERIDADES_POR_SERVICO = {
        "limpeza_praca": 1.5,
        "mato_alto": 1.5,
        "pintura_meio_fio": 1.5,
        "buraco_via_secundaria": 3.0,
        "iluminacao_publica": 3.0,
        "lampada_queimada": 3.0,
        "vazamento_agua": 4.0,
        "obstrucao_galeria_pluvial": 4.0,
        "semaforo_desligado": 5.0,
        "risco_desabamento": 5.0,
        "risco_deslizamento": 5.0,
    }
    SEVERIDADE_PADRAO = 3.0

    id = db.Column(db.Integer, primary_key=True)
    # O serviço usa a categoria normalizada informada pelo cliente.
    servico = db.Column(db.String(80), nullable=False, index=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    raio_agregacao_metros = db.Column(db.Float, nullable=False, default=100.0)
    severidade_base = db.Column(db.Float, nullable=False, default=SEVERIDADE_PADRAO)
    classificacao_geografica = db.Column(db.String(20), nullable=False, default="residencial")
    multiplicador_geografico = db.Column(db.Float, nullable=False, default=1.0)
    status = db.Column(db.String(20), nullable=False, default="aberta")
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    atualizado_em = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    chamados = db.relationship("Chamado", back_populates="ocorrencia")

    @property
    def quantidade_cidadaos(self):
        return len({chamado.solicitante_id for chamado in self.chamados})

    @property
    def horas_em_aberto(self):
        if not self.criado_em:
            return 0.0
        inicio = self.criado_em
        if inicio.tzinfo is None:
            inicio = inicio.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - inicio).total_seconds() / 3600)

    @property
    def score_criticidade(self):
        quantidade_cidadaos = max(1, self.quantidade_cidadaos)
        score = (
            self.severidade_base * self.multiplicador_geografico
            + self.ALFA_MOBILIZACAO * log(quantidade_cidadaos)
            + self.BETA_ENVELHECIMENTO_POR_HORA * self.horas_em_aberto
        )
        return min(10.0, round(score, 2))

    def to_dict(self, incluir_chamados=False):
        data = {
            "id": self.id,
            "servico": self.servico,
            "localizacao": {
                "latitude": self.latitude,
                "longitude": self.longitude,
            },
            "raio_agregacao_metros": self.raio_agregacao_metros,
            "status": self.status,
            "quantidade_chamados": len(self.chamados),
            "quantidade_cidadaos": self.quantidade_cidadaos,
            "criticidade": {
                "score": self.score_criticidade,
                "severidade_base": self.severidade_base,
                "multiplicador_geografico": self.multiplicador_geografico,
                "classificacao_geografica": self.classificacao_geografica,
                "horas_em_aberto": round(self.horas_em_aberto, 2),
                "alfa": self.ALFA_MOBILIZACAO,
                "beta_por_hora": self.BETA_ENVELHECIMENTO_POR_HORA,
            },
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }
        if incluir_chamados:
            data["chamados"] = [chamado.to_dict() for chamado in self.chamados]
        return data
