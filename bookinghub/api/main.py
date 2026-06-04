"""
main.py — Entrypoint da API BookingHub (FastAPI + psycopg2).
"""

from fastapi import FastAPI
from api.routers import voos, hoteis, reservas, pagamentos, relatorios, testes

app = FastAPI(
    title="BookingHub API",
    description="Plataforma de reservas de voos e hotéis — Trabalho Final BD",
    version="1.0.0",
)

app.include_router(voos.router,       prefix="/voos",      tags=["Voos"])
app.include_router(hoteis.router,     prefix="/hoteis",    tags=["Hotéis"])
app.include_router(reservas.router,   prefix="/reservas",  tags=["Reservas"])
app.include_router(pagamentos.router, prefix="/pagamentos",tags=["Pagamentos"])
app.include_router(relatorios.router, prefix="/relatorios",tags=["Relatórios"])
app.include_router(testes.router,     prefix="/test",      tags=["Testes"])


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "BookingHub API"}
