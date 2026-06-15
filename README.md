# 🛒 Mini E-commerce com Microsserviços

Este projeto é uma implementação de uma arquitetura de microsserviços para um mini e-commerce, focada em sistemas distribuídos, replicação de dados, tolerância a falhas (*Heartbeat*) e segurança via JWT.

Foi construído utilizando **Python**, **FastAPI** e orquestrado com **Docker Compose**.

---

# 🏗️ Arquitetura do Sistema

O sistema é composto por **4 serviços principais** rodando em containers isolados.

O **API Gateway** funciona como o único ponto de entrada (*North-South Traffic*) e gerencia o monitoramento de saúde da rede.

```text
       Cliente (Navegador, Postman, curl)
                      │
                      ▼
            ┌───────────────────┐
            │   API Gateway     │
            │    Porta 5000     │
            │ (Ponto Único +    │
            │      CORS)        │
            └────┬─────┬─────┬──┘
                 │     │     │
                 │     │     │
                 ▼     ▼     ▼
          ┌────────┐ ┌────────┐ ┌────────┐
          │Usuários│ │Produtos│ │Pedidos │
          │ :5001  │ │ :5002  │ │ :5003  │
          └────┬───┘ └────┬───┘ └────┬───┘
               │          │          │
               ▼          ▼          ▼
         Users DB   Réplicas 1 e 2  Orders DB
```

## ✨ Destaques da Implementação

### 📦 Replicação (Produtos)

* Consistência forte na escrita:

  * Os dados são salvos simultaneamente em dois arquivos JSON.
* Leitura distribuída:

  * Implementada utilizando algoritmo **Round-Robin** entre as réplicas.

### ❤️ Heartbeat (Gateway)

* Monitoramento contínuo em segundo plano.
* Caso algum serviço fique indisponível:

  * O Gateway detecta a falha.
  * Intercepta as requisições.
  * Retorna **503 Service Unavailable**.

### 🔐 Autenticação

* Implementada utilizando **JWT (JSON Web Token)**.
* Controle de acesso baseado em escopo:

  * `admin`
  * `user`

---

# 🚀 Como Executar o Projeto

O projeto foi totalmente containerizado, garantindo que rode em qualquer ambiente sem necessidade de instalar Python ou configurar variáveis locais.

## Pré-requisitos

* Docker instalado
* Docker Compose instalado

## Passo a Passo

Abra o terminal na raiz do projeto (onde está localizado o arquivo `docker-compose.yml`) e execute:

```bash
docker-compose up --build
```

Aguarde os containers iniciarem.

Nos logs será possível observar o Gateway realizando verificações de *Heartbeat* a cada 5 segundos para monitorar a saúde dos microsserviços.

### Encerrar a aplicação

```bash
docker-compose down
```

ou pressione:

```text
Ctrl + C
```

---

## 💾 Persistência de Dados

Os bancos de dados (arquivos `.json`) estão mapeados em volumes locais.

Dessa forma, os dados não serão perdidos quando os containers forem reiniciados.

---

# 🧪 Como Testar a Aplicação

## Opção 1: Swagger UI (Visão do Desenvolvedor)

Cada microsserviço disponibiliza documentação interativa via FastAPI.

### 👤 Serviço de Usuários

```text
http://localhost:5001/docs
```

### 📦 Serviço de Produtos

```text
http://localhost:5002/docs
```

### 🛒 Serviço de Pedidos

```text
http://localhost:5003/docs
```

---

## Opção 2: API Gateway (Visão de Produção)

Todas as requisições externas devem passar pelo Gateway na porta:

```text
http://localhost:5000
```

---

# 👤 Serviço de Usuários (`/users`)

| Método | Rota              | Descrição                          | Exemplo de Body                                                           |
| ------ | ----------------- | ---------------------------------- | ------------------------------------------------------------------------- |
| POST   | `/users/register` | Cria um usuário                    | `{"nome":"Admin","email":"admin@teste.com","senha":"123","role":"admin"}` |
| POST   | `/users/login`    | Login e geração do JWT             | `{"email":"admin@teste.com","senha":"123"}`                               |
| GET    | `/users/{id}`     | Busca um usuário (JWT obrigatório) | -                                                                         |

---

# 📦 Serviço de Produtos (`/products`)

| Método | Rota                      | Descrição                            | Exemplo de Body                                           |
| ------ | ------------------------- | ------------------------------------ | --------------------------------------------------------- |
| GET    | `/products/products`      | Lista catálogo (Round-Robin)         | -                                                         |
| GET    | `/products/products/{id}` | Detalha um produto                   | -                                                         |
| POST   | `/products/products`      | Cria produto (JWT Admin obrigatório) | `{"nome":"Teclado","descricao":"Mecânico","preco":150.0}` |

---

# 🛒 Serviço de Pedidos (`/orders`)

| Método | Rota                      | Descrição                     | Exemplo de Body                  |
| ------ | ------------------------- | ----------------------------- | -------------------------------- |
| POST   | `/orders/orders`          | Cria pedido (JWT obrigatório) | `{"productId":1,"quantidade":2}` |
| GET    | `/orders/orders/{userId}` | Lista pedidos do usuário      | -                                |

---

# 🛠️ Simulação de Falhas e Tolerância

Para validar o mecanismo de **Heartbeat** implementado no API Gateway:

## 1. Com o sistema em execução

Abra um novo terminal.

## 2. Derrube o serviço de Produtos

```bash
docker stop ms-products
```

## 3. Observe os logs do Gateway

Em até 5 segundos será exibida uma mensagem semelhante a:

```text
FALHA: Serviço products está fora do ar.
```

## 4. Teste o acesso ao catálogo

```text
http://localhost:5000/products/products
```

O Gateway responderá com:

```http
503 Service Unavailable
```

demonstrando que o serviço indisponível foi detectado corretamente.

---

## 🔄 Recuperação Automática

Reative o serviço:

```bash
docker start ms-products
```

O Gateway registrará a recuperação:

```text
RECUPERADO: Serviço products voltou ao ar.
```

e o tráfego será restabelecido automaticamente.

---

# 📚 Tecnologias Utilizadas

* Python
* FastAPI
* Docker
* Docker Compose
* JWT Authentication
* JSON File Storage
* REST APIs
* Heartbeat Monitoring
* Round-Robin Load Balancing
* Microservices Architecture
