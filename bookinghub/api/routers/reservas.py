from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_cursor
import psycopg2

router = APIRouter()

# ── Schemas ──────────────────────────────────────────────────────────────────

class ReservaVooIn(BaseModel):
    customer_id: int
    flight_id: int
    seat_number: str

class ReservaHotelIn(BaseModel):
    customer_id: int
    room_id: int
    check_in: str   # YYYY-MM-DD
    check_out: str  # YYYY-MM-DD

# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/voo")
def reservar_voo(body: ReservaVooIn):
    """Cria reserva de voo com SELECT FOR UPDATE (evita overbooking)."""
    with get_cursor() as (cur, conn):
        # Trava a linha do voo para leitura exclusiva
        cur.execute("""
            SELECT available_seats FROM flights
            WHERE id = %s FOR UPDATE
        """, (body.flight_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Voo não encontrado")
        if row["available_seats"] <= 0:
            raise HTTPException(409, "Sem assentos disponíveis para este voo")

        # Decrementa vagas e cria reserva atomicamente
        cur.execute("""
            UPDATE flights SET available_seats = available_seats - 1
            WHERE id = %s
        """, (body.flight_id,))
        cur.execute("""
            INSERT INTO flight_reservations (customer_id, flight_id, seat_number, status)
            VALUES (%s, %s, %s, 'pending')
            RETURNING id
        """, (body.customer_id, body.flight_id, body.seat_number))
        res_id = cur.fetchone()["id"]
        conn.commit()
        return {"reservation_id": res_id, "status": "pending"}


@router.post("/hotel")
def reservar_hotel(body: ReservaHotelIn):
    """Cria reserva de hotel verificando conflito de datas."""
    with get_cursor() as (cur, conn):
        # Trava o quarto
        cur.execute("SELECT id FROM rooms WHERE id = %s FOR UPDATE", (body.room_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Quarto não encontrado")

        # Verifica conflito de datas
        cur.execute("""
            SELECT id FROM hotel_reservations
            WHERE room_id = %s
              AND status != 'cancelled'
              AND check_in  < %s
              AND check_out > %s
        """, (body.room_id, body.check_out, body.check_in))
        if cur.fetchone():
            raise HTTPException(409, "Quarto indisponível para o período solicitado")

        # Calcula preço total
        cur.execute("SELECT price_per_night FROM rooms WHERE id = %s", (body.room_id,))
        price = cur.fetchone()["price_per_night"]
        from datetime import date
        nights = (date.fromisoformat(body.check_out) - date.fromisoformat(body.check_in)).days
        total = float(price) * nights

        cur.execute("""
            INSERT INTO hotel_reservations (customer_id, room_id, check_in, check_out, status, total_price)
            VALUES (%s, %s, %s, %s, 'pending', %s)
            RETURNING id
        """, (body.customer_id, body.room_id, body.check_in, body.check_out, total))
        res_id = cur.fetchone()["id"]
        conn.commit()
        return {"reservation_id": res_id, "total_price": total, "status": "pending"}


@router.get("/clientes/{customer_id}")
def historico_cliente(customer_id: int):
    """Retorna todas as reservas (voos + hotéis) de um cliente."""
    with get_cursor() as (cur, conn):
        cur.execute("""
            SELECT 'voo' AS tipo, fr.id AS reserva_id,
                   f.flight_number AS descricao,
                   f.departure_time AS data,
                   fr.status, p.amount
            FROM flight_reservations fr
            JOIN flights f ON f.id = fr.flight_id
            LEFT JOIN payments p ON p.reservation_id = fr.id
                AND p.reservation_type = 'flight'
            WHERE fr.customer_id = %s
            UNION ALL
            SELECT 'hotel', hr.id, h.name, hr.check_in::timestamptz,
                   hr.status, p.amount
            FROM hotel_reservations hr
            JOIN rooms r ON r.id = hr.room_id
            JOIN hotels h ON h.id = r.hotel_id
            LEFT JOIN payments p ON p.reservation_id = hr.id
                AND p.reservation_type = 'hotel'
            WHERE hr.customer_id = %s
            ORDER BY data DESC
        """, (customer_id, customer_id))
        return cur.fetchall()


@router.delete("/{tipo}/{reserva_id}")
def cancelar_reserva(tipo: str, reserva_id: int):
    """Cancela reserva e estorna disponibilidade."""
    if tipo not in ("voo", "hotel"):
        raise HTTPException(400, "tipo deve ser 'voo' ou 'hotel'")

    with get_cursor() as (cur, conn):
        if tipo == "voo":
            cur.execute("""
                UPDATE flight_reservations SET status = 'cancelled', updated_at = NOW()
                WHERE id = %s AND status != 'cancelled'
                RETURNING flight_id
            """, (reserva_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "Reserva não encontrada ou já cancelada")
            cur.execute("""
                UPDATE flights SET available_seats = available_seats + 1
                WHERE id = %s
            """, (row["flight_id"],))
        else:
            cur.execute("""
                UPDATE hotel_reservations SET status = 'cancelled'
                WHERE id = %s AND status != 'cancelled'
                RETURNING id
            """, (reserva_id,))
            if not cur.fetchone():
                raise HTTPException(404, "Reserva não encontrada ou já cancelada")

        # Marca pagamento como estornado (se existir)
        res_type = "flight" if tipo == "voo" else "hotel"
        cur.execute("""
            UPDATE payments SET status = 'refunded'
            WHERE reservation_type = %s AND reservation_id = %s
        """, (res_type, reserva_id))

        conn.commit()
        return {"status": "cancelled"}
