import os,tempfile
from pathlib import Path

fd,path=tempfile.mkstemp(suffix=".db")
os.close(fd)
os.environ["DATABASE_URL"]="sqlite:///"+path
os.environ["JWT_SECRET"]="TESTE-CHAVE-ISOLADA-APENAS-PYTEST"
from fastapi.testclient import TestClient
from app.main import app
from app.infrastructure.database import SessionLocal
from app.domain.models import Usuario, Unidade, Produto, Estoque
from app.application.security import hash_password
import pytest

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        with SessionLocal() as db:
            db.add_all([Usuario(nome="Admin",email="admin@example.com",senha_hash=hash_password("SenhaAdmin123"),perfil="ADMIN"),Unidade(nome="Centro",endereco="Rua teste"),Produto(nome="Tapioca",preco=20.0)])
            db.flush();db.add(Estoque(unidade_id=1,produto_id=1,quantidade=15));db.commit()
        yield c

def token(c,email,password):
    r=c.post("/auth/login",json={"email":email,"senha":password})
    assert r.status_code==200,r.text
    return {"Authorization":"Bearer "+r.json()["accessToken"]}

def test_fluxo_e_erros(client):
    c=client
    assert c.post("/usuarios",json={"nome":"Cliente Teste","email":"cliente@example.com","senha":"Cliente123"}).status_code==201
    auth=token(c,"cliente@example.com","Cliente123")
    admin=token(c,"admin@example.com","SenhaAdmin123")
    assert c.get("/pedidos").status_code==401
    assert c.post("/estoques/movimentacoes",headers=auth,json={"unidadeId":1,"produtoId":1,"tipo":"ENTRADA","quantidade":2}).status_code==403
    assert c.get("/produtos").status_code==200
    base={"unidadeId":1,"canalPedido":"TOTEM","itens":[{"produtoId":1,"quantidade":2}],"formaPagamento":"MOCK"}
    assert c.post("/pedidos",headers=auth,json={k:v for k,v in base.items() if k!="canalPedido"}).status_code==422
    assert c.post("/pedidos",headers=auth,json={**base,"itens":[{"produtoId":1,"quantidade":100}]}).status_code==409
    assert c.post("/pedidos",headers=auth,json={**base,"itens":[{"produtoId":999,"quantidade":1}]}).status_code==404
    created=c.post("/pedidos",headers=auth,json=base)
    assert created.status_code==201,created.text
    pid=created.json()["id"]
    assert created.json()["valorTotal"]==40.0
    assert len(c.get("/pedidos?canalPedido=TOTEM",headers=auth).json()["items"])==1
    payment={"pedidoId":pid,"resultado":"APROVADO","chaveIdempotencia":"teste-unico-001"}
    paid=c.post("/pagamentos",headers=auth,json=payment)
    assert paid.status_code==200 and paid.json()["statusPedido"]=="PAGO"
    repeated=c.post("/pagamentos",headers=auth,json=payment)
    assert repeated.json()["pagamentoId"]==paid.json()["pagamentoId"]
    assert c.patch(f"/pedidos/{pid}/status",headers=admin,json={"status":"EM_PREPARACAO"}).status_code==200
    assert c.get("/auditorias",headers=admin).status_code==200

def test_pagamento_recusado(client):
    c=client;auth=token(c,"cliente@example.com","Cliente123")
    p=c.post("/pedidos",headers=auth,json={"unidadeId":1,"canalPedido":"APP","itens":[{"produtoId":1,"quantidade":1}]}).json()["id"]
    r=c.post("/pagamentos",headers=auth,json={"pedidoId":p,"resultado":"RECUSADO","chaveIdempotencia":"recusa-unica-2"})
    assert r.status_code==200 and r.json()["statusPedido"]=="PAGAMENTO_RECUSADO"
    assert c.post(f"/pedidos/{p}/cancelamento",headers=auth).status_code==200
