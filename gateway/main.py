import asyncio
import httpx
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

app = FastAPI(title="API Gateway")

# --- CONFIGURAÇÃO DE CORS (Para seu futuro Front-end) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Em produção, coloque a URL do seu front
    allow_methods=["*"],
    allow_headers=["*"],
)

# URLs internas dos serviços no Docker
SERVICES = {
    "users": "http://ms-users:5001",
    "products": "http://ms-products:5002",
    "orders": "http://ms-orders:5003"
}

# Estado de saúde dos serviços
services_health = {name: True for name in SERVICES}

# --- MECANISMO DE HEARTBEAT ---
async def check_health():
    async with httpx.AsyncClient(timeout=2.0) as client:
        while True:
            for name, url in SERVICES.items():
                try:
                    response = await client.get(f"{url}/health")
                    if response.status_code == 200 and not services_health[name]:
                        print(f"[{datetime.now()}] RECUPERADO: Serviço {name} voltou a responder.")
                        services_health[name] = True
                    elif response.status_code != 200:
                        raise Exception()
                except Exception:
                    if services_health[name]:
                        print(f"[{datetime.now()}] FALHA: Serviço {name} está fora do ar.")
                    services_health[name] = False
            
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(check_health())

# --- ROTEAMENTO DINÂMICO (PROXY) ---
@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def gateway_proxy(service: str, path: str, request: Request):
    if service not in SERVICES:
        raise HTTPException(status_code=404, detail="Serviço não encontrado")
    
    if not services_health[service]:
        raise HTTPException(status_code=503, detail=f"Serviço {service} temporariamente indisponível (Heartbeat Failed)")

    url = f"{SERVICES[service]}/{service}/{path}"
    
    # Repassa a requisição original
    async with httpx.AsyncClient() as client:
        method = request.method
        content = await request.body()
        headers = dict(request.headers)
        # Remove o host original para não dar conflito no redirecionamento
        headers.pop("host", None)

        try:
            target_response = await client.request(
                method, url, content=content, headers=headers, params=request.query_params
            )
            return Response(
                content=target_response.content,
                status_code=target_response.status_code,
                headers=dict(target_response.headers)
            )
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Erro de comunicação com o serviço interno")