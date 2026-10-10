from datetime import datetime, timezone
from sqlalchemy import String, Integer, ForeignKey, Numeric, DateTime, Boolean, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database import Base

def now(): return datetime.now(timezone.utc)

class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    perfil: Mapped[str] = mapped_column(String(20), default="CLIENTE")
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=now)

class Unidade(Base):
    __tablename__ = "unidades"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    endereco: Mapped[str] = mapped_column(String(255))
    ativa: Mapped[bool] = mapped_column(Boolean, default=True)

class Produto(Base):
    __tablename__ = "produtos"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preco: Mapped[float] = mapped_column(Numeric(10,2))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

class Estoque(Base):
    __tablename__ = "estoques"
    __table_args__ = (UniqueConstraint("unidade_id", "produto_id"), CheckConstraint("quantidade >= 0"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    unidade_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"))
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"))
    quantidade: Mapped[int] = mapped_column(Integer, default=0)

class Pedido(Base):
    __tablename__ = "pedidos"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    unidade_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"))
    canalPedido: Mapped[str] = mapped_column(String(20))
    valor_total: Mapped[float] = mapped_column(Numeric(10,2))
    status: Mapped[str] = mapped_column(String(30),default="AGUARDANDO_PAGAMENTO")
    criado_em: Mapped[datetime] = mapped_column(DateTime,default=now)

class ItemPedido(Base):
    __tablename__ = "itens_pedido"
    __table_args__ = (CheckConstraint("quantidade > 0"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"))
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"))
    quantidade: Mapped[int] = mapped_column(Integer)
    preco_unitario: Mapped[float] = mapped_column(Numeric(10,2))

class Pagamento(Base):
    __tablename__ = "pagamentos"
    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"))
    valor: Mapped[float] = mapped_column(Numeric(10,2))
    status: Mapped[str] = mapped_column(String(20))
    transacao_mock: Mapped[str] = mapped_column(String(100), unique=True)
    chave_idempotencia: Mapped[str] = mapped_column(String(100), unique=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime,default=now)

class MovimentacaoEstoque(Base):
    __tablename__ = "movimentacoes_estoque"
    id: Mapped[int] = mapped_column(primary_key=True)
    estoque_id: Mapped[int] = mapped_column(ForeignKey("estoques.id"))
    tipo: Mapped[str] = mapped_column(String(10))
    quantidade: Mapped[int] = mapped_column(Integer)
    data_movimentacao: Mapped[datetime] = mapped_column(DateTime, default=now)

class Auditoria(Base):
    __tablename__ = "auditorias"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    pedido_id: Mapped[int | None] = mapped_column(ForeignKey("pedidos.id"),nullable=True)
    acao: Mapped[str] = mapped_column(String(100))
    data_registro: Mapped[datetime] = mapped_column(DateTime,default=now)
