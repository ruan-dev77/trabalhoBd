from fastapi import APIRouter, Query
from typing import Optional
from database import get_cursor

router = APIRouter()

@router.get("/ocupacao")
def ocupacao(
    data_inicio: Optional[str] = Query(None, description="YYYY-MM-DD"),
    data_fim: Optional[str] = Query(None, description="YYYY-MM-DD"),
):
    sql = """
        SELECT f.flight_number,
               COUNT(fr.id) AS total_reservas,
               f.total_seats,
               ROUND(COUNT(fr.id)::numeric / f.total_seats * 100, 2) AS ocupacao_pct
        FROM flights f
        LEFT JOIN flight_reservations fr ON fr.flight_id = f.id
            AND fr.status = 'confirmed'
        WHERE 1=1
    """
    params = []
    if data_inicio:
        sql += " AND f.departure_time >= %s"
        params.append(data_inicio)
    if data_fim:
        sql += " AND f.departure_time <= %s"
        params.append(data_fim)
    sql += " GROUP BY f.id, f.flight_number, f.total_seats ORDER BY ocupacao_pct DESC LIMIT 20"

    with get_cursor() as (cur, conn):
        cur.execute(sql, params)
        return cur.fetchall()
