from fastapi import APIRouter, Query
from typing import Optional
from database import get_cursor

router = APIRouter()

@router.get("/disponiveis")
def voos_disponiveis(
    origem: Optional[str] = Query(None, description="Cidade de origem"),
    destino: Optional[str] = Query(None, description="Cidade de destino"),
    data_ida: Optional[str] = Query(None, description="Data (YYYY-MM-DD)"),
):
    sql = """
        SELECT f.id, f.flight_number, f.departure_time, f.arrival_time,
               f.available_seats, f.price,
               a1.code AS origin, a1.city AS origin_city,
               a2.code AS destination, a2.city AS destination_city
        FROM flights f
        JOIN airports a1 ON a1.id = f.origin_airport_id
        JOIN airports a2 ON a2.id = f.destination_airport_id
        WHERE f.available_seats > 0
    """
    params = []
    if origem:
        sql += " AND a1.city ILIKE %s"
        params.append(f"%{origem}%")
    if destino:
        sql += " AND a2.city ILIKE %s"
        params.append(f"%{destino}%")
    if data_ida:
        sql += " AND DATE(f.departure_time) = %s"
        params.append(data_ida)
    sql += " ORDER BY f.departure_time LIMIT 100"

    with get_cursor() as (cur, conn):
        cur.execute(sql, params)
        return cur.fetchall()
