from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_cursor

router = APIRouter()

class PagamentoIn(BaseModel):
    reservation_type: str   # "flight" ou "hotel"
    reservation_id: int
    amount: float
    payment_method: str     # credit_card, debit_card, pix, boleto

@router.post("/")
def registrar_pagamento(body: PagamentoIn):
    if body.reservation_type not in ("flight", "hotel"):
        raise HTTPException(400, "reservation_type deve ser 'flight' ou 'hotel'")

    with get_cursor() as (cur, conn):
        # Registra pagamento
        cur.execute("""
            INSERT INTO payments (reservation_type, reservation_id, amount, status, payment_method)
            VALUES (%s, %s, %s, 'completed', %s)
            RETURNING id
        """, (body.reservation_type, body.reservation_id, body.amount, body.payment_method))
        pay_id = cur.fetchone()["id"]

        # Confirma a reserva
        table = "flight_reservations" if body.reservation_type == "flight" else "hotel_reservations"
        cur.execute(f"""
            UPDATE {table} SET status = 'confirmed', updated_at = NOW()
            WHERE id = %s AND status = 'pending'
        """, (body.reservation_id,))

        conn.commit()
        return {"payment_id": pay_id, "status": "completed"}
