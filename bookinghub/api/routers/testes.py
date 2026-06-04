from fastapi import APIRouter
from database import get_cursor

router = APIRouter()

@router.post("/falha-transacao")
def falha_transacao():
    """
    Parte 3 — demonstra ROLLBACK automático.
    Insere uma reserva mas lança exceção antes do COMMIT.
    """
    try:
        with get_cursor() as (cur, conn):
            cur.execute("""
                INSERT INTO flight_reservations (customer_id, flight_id, seat_number, status)
                VALUES (1, 1, '99Z', 'pending')
                RETURNING id
            """)
            res_id = cur.fetchone()["id"]
            raise Exception("Falha simulada antes do COMMIT!")
            conn.commit()
    except Exception as e:
        # Verifica que o registro NÃO foi salvo
        with get_cursor() as (cur, conn):
            cur.execute("SELECT COUNT(*) AS c FROM flight_reservations WHERE seat_number = '99Z'")
            count = cur.fetchone()["c"]
        return {
            "erro": str(e),
            "rollback_aplicado": True,
            "registro_persistido": count > 0
        }
