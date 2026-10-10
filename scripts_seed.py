"""Cria registros de demonstração; execute: python scripts_seed.py"""
from sqlalchemy import select
from app.infrastructure.database import Base, engine, SessionLocal
from app.domain.models import Usuario, Unidade, Produto, Estoque
from app.application.security import hash_password

Base.metadata.create_all(engine)
with SessionLocal() as db:
    if not db.scalar(select(Usuario).where(Usuario.email=="admin@raizes.example.com")):
        db.add(Usuario(nome="Administrador Demo",email="admin@raizes.example.com",senha_hash=hash_password("AdminDemo@123"),perfil="ADMIN"))
    if not db.scalar(select(Usuario).where(Usuario.email=="cozinha@raizes.example.com")):
        db.add(Usuario(nome="Cozinha Demo",email="cozinha@raizes.example.com",senha_hash=hash_password("CozinhaDemo@123"),perfil="COZINHA"))
    db.flush()
    if not db.scalar(select(Unidade).where(Unidade.nome=="Unidade Centro")):
        db.add(Unidade(nome="Unidade Centro",endereco="Endereço fictício - demonstração",ativa=True))
    if not db.scalar(select(Produto).where(Produto.nome=="Tapioca de queijo")):
        db.add(Produto(nome="Tapioca de queijo",descricao="Produto demonstrativo",preco=22.95,ativo=True))
    db.flush()
    u=db.scalar(select(Unidade).where(Unidade.nome=="Unidade Centro"))
    prod=db.scalar(select(Produto).where(Produto.nome=="Tapioca de queijo"))
    if not db.scalar(select(Estoque).where(Estoque.unidade_id==u.id,Estoque.produto_id==prod.id)):
        db.add(Estoque(unidade_id=u.id,produto_id=prod.id,quantidade=30))
    db.commit()
print("Dados demonstrativos prontos. Use apenas em ambiente local.")
