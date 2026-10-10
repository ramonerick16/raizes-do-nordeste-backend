from typing import Literal
from decimal import Decimal
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class Cadastro(BaseModel):
    nome: str = Field(min_length=2,max_length=120)
    email: EmailStr
    senha: str = Field(min_length=8)
class Login(BaseModel):
    email: EmailStr
    senha: str
class UnidadeIn(BaseModel):
    nome: str=Field(min_length=2)
    endereco: str=Field(min_length=3)
class ProdutoIn(BaseModel):
    nome:str
    descricao:str|None=None
    preco:Decimal=Field(gt=0,decimal_places=2)
class EstoqueIn(BaseModel):
    unidadeId:int
    produtoId:int
    tipo:Literal["ENTRADA","SAIDA"]
    quantidade:int=Field(gt=0)
class ItemIn(BaseModel):
    produtoId:int
    quantidade:int=Field(gt=0)
class PedidoIn(BaseModel):
    unidadeId:int
    canalPedido:Literal["APP","TOTEM","BALCAO","PICKUP","WEB"]
    itens:list[ItemIn]=Field(min_length=1)
    formaPagamento:Literal["MOCK"]="MOCK"
class PagamentoIn(BaseModel):
    pedidoId:int
    resultado:Literal["APROVADO","RECUSADO"]
    chaveIdempotencia:str=Field(min_length=5,max_length=100)
class StatusIn(BaseModel):
    status:Literal["EM_PREPARACAO","PRONTO","ENTREGUE"]
