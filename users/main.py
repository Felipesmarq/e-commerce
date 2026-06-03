import json
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import bcrypt
from jose import JWTError, jwt

# --- CONFIGURAÇÕES GERAIS ---
# Carrega as variáveis do arquivo .env para o sistema
load_dotenv()

# --- CONFIGURAÇÕES GERAIS ---
DB_FILE = "users.json"

# os.getenv busca a variável. Se não existir, usa o segundo parâmetro como padrão (fallback).
SECRET_KEY = os.getenv("SECRET_KEY", "chave_insegura_de_desenvolvimento")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# Como variáveis de ambiente chegam como texto (string), precisamos converter os minutos para número (int)
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

def get_password_hash(password: str) -> str:
    """Gera o hash da senha usando o bcrypt nativo"""
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha em texto plano bate com o hash salvo"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
security = HTTPBearer()

app = FastAPI(title="Serviço de Usuários")

# --- MODELOS ---
class UserRegister(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    role: str = "user" 

class UserLogin(BaseModel):
    email: EmailStr
    senha: str

# --- FUNÇÕES DE BANCO DE DADOS (JSON) ---
def read_db():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r") as f:
        return json.load(f)

def write_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- FUNÇÕES DE AUTENTICAÇÃO ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
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

@app.post("/users/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserRegister):
    users = read_db()
    
    # Verifica se e-mail já existe
    for u in users:
        if u["email"] == user.email:
            raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    
    # Cria o novo usuário
    new_user = {
        "id": len(users) + 1,
        "nome": user.nome,
        "email": user.email,
        "senha": get_password_hash(user.senha),
        "role": user.role
    }
    
    users.append(new_user)
    write_db(users)
    
    return {"message": "Usuário criado com sucesso!", "id": new_user["id"]}

@app.post("/users/login")
async def login(user: UserLogin):
    users = read_db()
    
    # Busca usuário
    db_user = next((u for u in users if u["email"] == user.email), None)
    
    # Verifica credenciais
    if not db_user or not verify_password(user.senha, db_user["senha"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos"
        )
    
    # Gera JWT conforme regras da atividade (userId, email, role, exp)
    token_data = {
        "userId": db_user["id"],
        "email": db_user["email"],
        "role": db_user["role"]
    }
    token = create_access_token(token_data)
    
    return {"access_token": token, "token_type": "bearer"}

@app.get("/users/{user_id}")
async def get_user(user_id: int, current_user: dict = Depends(verify_token)):
    users = read_db()
    db_user = next((u for u in users if u["id"] == user_id), None)
    
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Regra de segurança: Um usuário normal só pode ver os próprios dados
    if current_user["role"] != "admin" and current_user["userId"] != user_id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para ver este usuário")
    
    return {
        "id": db_user["id"],
        "nome": db_user["nome"],
        "email": db_user["email"],
        "role": db_user["role"]
    }