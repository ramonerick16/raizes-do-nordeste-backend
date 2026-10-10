from contextlib import asynccontextmanager
from decimal import Decimal
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.infrastructure.database import Base, engine, get_db
from app.domain.models import Usuario, Unidade, Produto, Estoque, Pedido, ItemPedido, Pagamento, MovimentacaoEstoque, Auditoria
from app.api.schemas import Cadastro, Login, UnidadeIn, ProdutoIn, EstoqueIn, PedidoIn, PagamentoIn, StatusIn
from app.application.security import hash_password,check_password,issue_token,current_user,allowed

def fail(code, message, status, details=None):
    raise HTTPException(status, detail={"error":code,"message":message,"details":details or []})
def serialize(obj):
    return {c.name: (float(getattr(obj,c.name)) if isinstance(getattr(obj,c.name),Decimal) else getattr(obj,c.name).isoformat() if hasattr(getattr(obj,c.name),"isoformat") else getattr(obj,c.name)) for c in obj.__table__.columns if c.name != "senha_hash"}
def audit(db,user,action,pedido=None):
    db.add(Auditoria(usuario_id=user.id, pedido_id=pedido, acao=action))

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    yield
app = FastAPI(title="API Raízes do Nordeste",version="1.0.0",description="API educacional para rede de lanchonetes. Pagamentos são simulados.",lifespan=lifespan)

@app.exception_handler(HTTPException)
async def http_error(request:Request,exc:HTTPException):
    detail = exc.detail
    if isinstance(detail,dict): body=detail
    else: body={"error":"ERRO_HTTP","message":str(detail),"details":[]}
    return JSONResponse(status_code=exc.status_code,content={**body,"path":request.url.path},headers=exc.headers)
@app.exception_handler(RequestValidationError)
async def request_error(request:Request,exc:RequestValidationError):
    details=[{"field":".".join(str(p) for p in e["loc"]),"issue":e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422,content={"error":"DADOS_INVALIDOS","message":"Verifique os campos enviados.","details":details,"path":request.url.path})

@app.get("/",tags=["Sistema"])
def home(): return {"projeto":"Raízes do Nordeste","swagger":"/docs","status":"ativo"}

@app.post("/usuarios",status_code=201,tags=["Usuários"])
def cadastrar(data:Cadastro,db:Session=Depends(get_db)):
    if db.scalar(select(Usuario).where(Usuario.email==data.email.lower())): fail("EMAIL_DUPLICADO","E-mail já cadastrado",409)
    user=Usuario(nome=data.nome,email=data.email.lower(),senha_hash=hash_password(data.senha),perfil="CLIENTE")
    db.add(user);db.commit();db.refresh(user)
    return {"id":user.id,"nome":user.nome,"email":user.email,"perfil":user.perfil}

@app.post("/auth/login",tags=["Autenticação"])
def login(data:Login,db:Session=Depends(get_db)):
    user=db.scalar(select(Usuario).where(Usuario.email==data.email.lower()))
    if not user or not check_password(data.senha,user.senha_hash): fail("CREDENCIAIS_INVALIDAS","E-mail ou senha incorretos",401)
    return {"accessToken":issue_token(user),"tokenType":"bearer","perfil":user.perfil}

@app.get("/unidades",tags=["Unidades"])
def unidades(db:Session=Depends(get_db)): return [serialize(x) for x in db.scalars(select(Unidade)).all()]
@app.post("/unidades",status_code=201,tags=["Unidades"])
def criar_unidade(data:UnidadeIn,user=Depends(allowed("ADMIN")),db:Session=Depends(get_db)):
    u=Unidade(**data.model_dump());db.add(u);db.flush();audit(db,user,"CRIAR_UNIDADE");db.commit();db.refresh(u);return serialize(u)

@app.get("/produtos",tags=["Produtos"])
def produtos(unidadeId:int|None=None,page:int=Query(1,ge=1),limit:int=Query(10,ge=1,le=100),db:Session=Depends(get_db)):
    query=select(Produto).where(Produto.ativo==True)
    if unidadeId is not None: query=query.join(Estoque,Estoque.produto_id==Produto.id).where(Estoque.unidade_id==unidadeId)
    rows=db.scalars(query.offset((page-1)*limit).limit(limit)).all()
    return {"page":page,"limit":limit,"items":[serialize(x) for x in rows]}
@app.post("/produtos",status_code=201,tags=["Produtos"])
def criar_produto(data:ProdutoIn,user=Depends(allowed("ADMIN","GERENTE")),db:Session=Depends(get_db)):
    produto=Produto(**data.model_dump());db.add(produto);db.flush();audit(db,user,"CRIAR_PRODUTO");db.commit();db.refresh(produto);return serialize(produto)

@app.get("/estoques",tags=["Estoques"])
def estoques(unidadeId:int=Query(...),user=Depends(current_user),db:Session=Depends(get_db)):
    return [serialize(e) for e in db.scalars(select(Estoque).where(Estoque.unidade_id==unidadeId)).all()]
@app.post("/estoques/movimentacoes",status_code=201,tags=["Estoques"])
def movimentar(data:EstoqueIn,user=Depends(allowed("ADMIN","GERENTE")),db:Session=Depends(get_db)):
    if not db.get(Unidade,data.unidadeId) or not db.get(Produto,data.produtoId): fail("NAO_ENCONTRADO","Unidade ou produto inexistente",404)
    e=db.scalar(select(Estoque).where(Estoque.unidade_id==data.unidadeId,Estoque.produto_id==data.produtoId))
    if not e:
        if data.tipo=="SAIDA": fail("ESTOQUE_INSUFICIENTE","Sem estoque disponível",409)
        e=Estoque(unidade_id=data.unidadeId,produto_id=data.produtoId,quantidade=0);db.add(e);db.flush()
    novo=e.quantidade+(data.quantidade if data.tipo=="ENTRADA" else -data.quantidade)
    if novo<0:fail("ESTOQUE_INSUFICIENTE","Quantidade superior ao saldo",409)
    e.quantidade=novo;db.add(MovimentacaoEstoque(estoque_id=e.id,tipo=data.tipo,quantidade=data.quantidade));audit(db,user,"MOVIMENTAR_ESTOQUE");db.commit()
    return {"estoqueId":e.id,"saldo":novo}

def get_order(db,pid,user):
    order=db.get(Pedido,pid)
    if not order:fail("PEDIDO_NAO_ENCONTRADO","Pedido inexistente",404)
    if user.perfil=="CLIENTE" and order.usuario_id!=user.id:fail("SEM_PERMISSAO","Pedido não pertence ao usuário",403)
    return order

@app.post("/pedidos",status_code=201,tags=["Pedidos"])
def criar_pedido(data:PedidoIn,user=Depends(current_user),db:Session=Depends(get_db)):
    unidade=db.get(Unidade,data.unidadeId)
    if not unidade or not unidade.ativa:fail("UNIDADE_NAO_ENCONTRADA","Unidade não disponível",404)
    items={}
    for it in data.itens:items[it.produtoId]=items.get(it.produtoId,0)+it.quantidade
    total=Decimal("0")
    detalhes=[]
    for pid,qty in items.items():
        product=db.get(Produto,pid)
        if not product or not product.ativo:fail("PRODUTO_NAO_ENCONTRADO","Produto não encontrado",404)
        stock=db.scalar(select(Estoque).where(Estoque.unidade_id==data.unidadeId,Estoque.produto_id==pid))
        if not stock or stock.quantidade<qty:fail("ESTOQUE_INSUFICIENTE",f"Estoque insuficiente do produto {pid}",409)
        total+=product.preco*qty;detalhes.append((product,stock,qty))
    order=Pedido(usuario_id=user.id,unidade_id=data.unidadeId,canalPedido=data.canalPedido,valor_total=total)
    db.add(order);db.flush()
    for product,stock,qty in detalhes:
        db.add(ItemPedido(pedido_id=order.id,produto_id=product.id,quantidade=qty,preco_unitario=product.preco))
        # Reserva simplificada: baixa no momento de criação do pedido.
        stock.quantidade-=qty
        db.add(MovimentacaoEstoque(estoque_id=stock.id,tipo="SAIDA",quantidade=qty))
    audit(db,user,"CRIAR_PEDIDO",order.id);db.commit();db.refresh(order)
    return {"id":order.id,"unidadeId":order.unidade_id,"canalPedido":order.canalPedido,"valorTotal":float(order.valor_total),"status":order.status}

@app.get("/pedidos",tags=["Pedidos"])
def listar_pedidos(canalPedido:str|None=None,status:str|None=None,page:int=Query(1,ge=1),limit:int=Query(10,ge=1,le=100),user=Depends(current_user),db:Session=Depends(get_db)):
    q=select(Pedido)
    if user.perfil=="CLIENTE": q=q.where(Pedido.usuario_id==user.id)
    if canalPedido:
        if canalPedido not in {"APP","TOTEM","BALCAO","PICKUP","WEB"}:fail("CANAL_INVALIDO","Canal de pedido inválido",422)
        q=q.where(Pedido.canalPedido==canalPedido)
    if status:q=q.where(Pedido.status==status)
    return {"page":page,"items":[serialize(i) for i in db.scalars(q.order_by(Pedido.id.desc()).offset((page-1)*limit).limit(limit)).all()]}
@app.get("/pedidos/{id}",tags=["Pedidos"])
def consultar_pedido(id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    order=get_order(db,id,user)
    return {**serialize(order),"itens":[serialize(i) for i in db.scalars(select(ItemPedido).where(ItemPedido.pedido_id==id)).all()]}
@app.patch("/pedidos/{id}/status",tags=["Pedidos"])
def status_pedido(id:int,data:StatusIn,user=Depends(allowed("ADMIN","GERENTE","COZINHA")),db:Session=Depends(get_db)):
    order=get_order(db,id,user)
    trans={"PAGO":"EM_PREPARACAO","EM_PREPARACAO":"PRONTO","PRONTO":"ENTREGUE"}
    if trans.get(order.status)!=data.status:fail("TRANSICAO_INVALIDA","Transição de status não permitida",409)
    order.status=data.status;audit(db,user,"ATUALIZAR_STATUS",order.id);db.commit();return {"pedidoId":id,"status":order.status}
@app.post("/pedidos/{id}/cancelamento",tags=["Pedidos"])
def cancelar(id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    order=get_order(db,id,user)
    if order.status not in {"AGUARDANDO_PAGAMENTO","PAGAMENTO_RECUSADO"}:fail("CANCELAMENTO_INDISPONIVEL","Pedido não pode ser cancelado neste estado",409)
    for it in db.scalars(select(ItemPedido).where(ItemPedido.pedido_id==id)).all():
        stock=db.scalar(select(Estoque).where(Estoque.unidade_id==order.unidade_id,Estoque.produto_id==it.produto_id))
        stock.quantidade+=it.quantidade
        db.add(MovimentacaoEstoque(estoque_id=stock.id,tipo="ENTRADA",quantidade=it.quantidade))
    order.status="CANCELADO";audit(db,user,"CANCELAR_PEDIDO",id);db.commit();return {"pedidoId":id,"status":order.status}

@app.post("/pagamentos",tags=["Pagamentos"])
def pagar(data:PagamentoIn,user=Depends(current_user),db:Session=Depends(get_db)):
    order=get_order(db,data.pedidoId,user)
    existing=db.scalar(select(Pagamento).where(Pagamento.chave_idempotencia==data.chaveIdempotencia))
    if existing:
        if existing.pedido_id!=order.id:fail("CHAVE_EM_USO","Chave já usada em outro pedido",409)
        return {"pagamentoId":existing.id,"pedidoId":order.id,"status":existing.status,"valor":float(existing.valor)}
    if order.status not in {"AGUARDANDO_PAGAMENTO","PAGAMENTO_RECUSADO"}:fail("PEDIDO_INDISPONIVEL","Pedido não aceita novo pagamento",409)
    payment=Pagamento(pedido_id=order.id,valor=order.valor_total,status=data.resultado,transacao_mock="TEMP",chave_idempotencia=data.chaveIdempotencia)
    db.add(payment);db.flush();payment.transacao_mock=f"MOCK-{payment.id:05d}"
    order.status="PAGO" if data.resultado=="APROVADO" else "PAGAMENTO_RECUSADO"
    audit(db,user,"PAGAMENTO_"+data.resultado,order.id);db.commit()
    return {"pagamentoId":payment.id,"pedidoId":order.id,"status":payment.status,"valor":float(payment.valor),"transacaoMock":payment.transacao_mock,"statusPedido":order.status}
@app.get("/pagamentos/{id}",tags=["Pagamentos"])
def consultar_pagamento(id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    pay=db.get(Pagamento,id)
    if not pay:fail("PAGAMENTO_NAO_ENCONTRADO","Pagamento inexistente",404)
    get_order(db,pay.pedido_id,user)
    return serialize(pay)
@app.get("/auditorias",tags=["Auditoria"])
def logs(user=Depends(allowed("ADMIN")),db:Session=Depends(get_db)):
    return [serialize(r) for r in db.scalars(select(Auditoria).order_by(Auditoria.id.desc()).limit(100)).all()]
