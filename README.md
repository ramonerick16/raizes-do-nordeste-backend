Instalação e execução
Execute os comandos no terminal do Visual Studio Code, utilizando o PowerShell:
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python scripts_seed.py
uvicorn app.main:app --reload
Antes de utilizar a API, configure uma chave JWT segura no arquivo .env.

Acesso à API
API local: http://127.0.0.1:8000
Documentação Swagger: http://127.0.0.1:8000/docs
Especificação OpenAPI: http://127.0.0.1:8000/openapi.json

Testes
Os testes podem ser realizados pelo Swagger e pela coleção Postman disponível na pasta postman.
O comando python scripts_seed.py prepara os dados demonstrativos necessários para as verificações iniciais.