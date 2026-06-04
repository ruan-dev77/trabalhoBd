# BookingHub — Plataforma de Reservas

Trabalho Final da disciplina de Banco de Dados.

## Pré-requisitos

- [Docker](https://www.docker.com/) e Docker Compose instalados

## Como executar

```bash
# 1. Clone o repositório
git clone <url-do-repositorio>
cd bookinghub

# 2. Suba os containers
docker compose up -d

# 3. Aguarde o banco inicializar e rode o schema + seed
docker compose exec db psql -U booking -d bookinghub -f /sql/schema.sql
docker compose exec api python seed.py

# 4. Acesse a API
# http://localhost:8000/docs  ← documentação interativa (Swagger)
```

## Estrutura do projeto

```
bookinghub/
├── docker-compose.yml       # Orquestração dos containers
├── postgresql.conf          # Configurações customizadas do PostgreSQL
├── sql/
│   └── schema.sql           # DDL: criação das tabelas e índices
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py              # Entrypoint FastAPI
│   ├── database.py          # Conexão com psycopg2
│   ├── routers/             # Endpoints organizados por domínio
│   └── seed.py              # Script de carga de dados (10k+ registros)
├── testes/
│   ├── test_overbooking.py  # Teste concorrente de overbooking
│   ├── test_hotel_conflito.py
│   └── test_isolamento.py   # Suite de níveis de isolamento
└── backup/
    ├── backup_logico.sh     # pg_dump
    ├── backup_fisico.sh     # pg_basebackup + PITR
    └── restore.sh
```

## Partes do trabalho

| Parte | Descrição | Status |
|-------|-----------|--------|
| Schema + Seed | Modelo de dados e carga inicial | ⬜ |
| Parte 1 | Processamento de Consultas (índices + EXPLAIN) | ⬜ |
| Parte 2 | Transações e Controle de Concorrência | ⬜ |
| Parte 3 | Recuperação de Falhas (WAL + Backup) | ⬜ |
