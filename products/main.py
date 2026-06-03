import json
import os
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError, jwt
from dotenv import load_dotenv, find_dotenv

# Procura o arquivo .env automaticamente nas pastas acima
load_dotenv(find_dotenv())

# --- CONFIGURAÇÕES GERAIS ---
SECRET_KEY = os.getenv("SECRET_KEY", "chave_insegura_de_desenvolvimento")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# Variáveis para a Replicação
REPLICA1_FILE = "db_replica1.json"
REPLICA2_FILE = "db_replica2.json"

# Variável global para controlar de qual réplica vamos ler (Round-Robin)
current_replica = 0 

security = HTTPBearer()
app = FastAPI(title="Serviço de Produtos")

# --- MODELOS ---
class ProductCreate(BaseModel):
    nome: str
    descricao: str
    preco: float

# --- FUNÇÕES DE REPLICAÇÃO E BANCO DE DADOS ---

def read_db():
    """Lê alternando entre a réplica 1 e a réplica 2 (Round-Robin)"""
    global current_replica
    
    # Decide qual arquivo ler
    file_to_read = REPLICA1_FILE if current_replica == 0 else REPLICA2_FILE
    
    # Alterna o valor para a próxima requisição (se for 0 vira 1, se for 1 vira 0)
    current_replica = 1 - current_replica
    
    # Adicionamos o nome da réplica no log para você ver o Round-Robin funcionando!
    print(f"Lendo dados do arquivo: {file_to_read}")

    if not os.path.exists(file_to_read):
        return []
    
    with open(file_to_read, "r") as f:
        return json.load(f)

def write_db(data):
    """Escreve a mesma informação nas DUAS réplicas (Consistência Forte)"""
    with open(REPLICA1_FILE, "w") as f:
        json.dump(data, f, indent=4)
        
    with open(REPLICA2_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- FUNÇÕES DE AUTENTICAÇÃO ---

def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Valida o JWT e verifica se o usuário tem a role 'admin'"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # A grande regra de negócio aqui:
        if payload.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Acesso negado. Apenas administradores podem criar produtos."
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

# --- ROTAS ---

@app.get("/health")
async def health_check():
    """Endpoint para o Heartbeat do API Gateway"""
    return {"status": "ok"}

@app.get("/products")
async def list_products():
    """Lista produtos usando leitura distribuída"""
    products = read_db()
    return products

@app.get("/products/{product_id}")
async def get_product(product_id: int):
    """Detalha um produto usando leitura distribuída"""
    products = read_db()
    product = next((p for p in products if p["id"] == product_id), None)
    
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    return product

@app.post("/products", status_code=status.HTTP_201_CREATED)
async def create_product(product: ProductCreate, admin_user: dict = Depends(verify_admin_token)):
    """Cria um produto. Requer Token JWT de Admin. Grava nas duas réplicas."""
    # Para garantir consistência forte, lemos da base atual para descobrir o próximo ID
    products = read_db()
    
    new_product = {
        "id": len(products) + 1,
        "nome": product.nome,
        "descricao": product.descricao,
        "preco": product.preco
    }
    
    products.append(new_product)
    
    # Escreve nos DOIS arquivos antes de devolver o sucesso ao usuário
    write_db(products)
    
    return {"message": "Produto criado e replicado com sucesso!", "product": new_product}