import json
import os
import httpx
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError, jwt
from dotenv import load_dotenv, find_dotenv

# Carrega as configurações do .env na raiz
load_dotenv(find_dotenv())

# --- CONFIGURAÇÕES GERAIS ---
SECRET_KEY = os.getenv("SECRET_KEY", "chave_insegura_de_desenvolvimento")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
DB_FILE = "orders.json"

PRODUCTS_SERVICE_URL = os.getenv("PRODUCTS_SERVICE_URL", "http://localhost:5002")

security = HTTPBearer()
app = FastAPI(title="Serviço de Pedidos")

# --- MODELOS ---
class OrderCreate(BaseModel):
    productId: int
    quantidade: int = 1

# --- FUNÇÕES DE BANCO DE DADOS ---
def read_db():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r") as f:
        return json.load(f)

def write_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- FUNÇÕES DE AUTENTICAÇÃO ---
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Valida o token e extrai os dados do usuário"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
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

@app.post("/orders", status_code=status.HTTP_201_CREATED)
async def create_order(order: OrderCreate, current_user: dict = Depends(verify_token)):
    """Cria um pedido. O userId é extraído do próprio token JWT."""
    user_id = current_user.get("userId")
    
    # 1. Comunicação Inter-serviços: Verifica se o produto existe no Serviço de Produtos!
    async with httpx.AsyncClient() as client:
        try:
            # Faz um GET na API de Produtos
            response = await client.get(f"{PRODUCTS_SERVICE_URL}/products/{order.productId}")
            
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Produto não existe no catálogo.")
            elif response.status_code != 200:
                raise HTTPException(status_code=500, detail="Erro ao consultar o Serviço de Produtos.")
            
            produto_data = response.json()
            
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Serviço de Produtos está fora do ar (Indisponível).")

    # 2. Registra o Pedido
    orders = read_db()
    
    # Calculando o valor total usando o preço retornado pelo microsserviço de Produtos
    valor_total = produto_data["preco"] * order.quantidade
    
    new_order = {
        "id": len(orders) + 1,
        "userId": user_id,
        "productId": order.productId,
        "nome_produto": produto_data["nome"], # Salvamos o nome pro recibo ficar bonito
        "quantidade": order.quantidade,
        "valor_total": valor_total,
        "status": "Aprovado"
    }
    
    orders.append(new_order)
    write_db(orders)
    
    return {"message": "Pedido realizado com sucesso!", "order": new_order}

@app.get("/orders/{userId}")
async def get_user_orders(userId: int, current_user: dict = Depends(verify_token)):
    """Lista pedidos de um usuário. Usuário só pode ver os próprios pedidos (ou admin vê todos)."""
    
    # Regra de Segurança
    if current_user["role"] != "admin" and current_user["userId"] != userId:
        raise HTTPException(status_code=403, detail="Acesso negado. Você só pode ver seus próprios pedidos.")
    
    orders = read_db()
    user_orders = [o for o in orders if o["userId"] == userId]
    
    return user_orders