from fastapi import APIRouter, Query
from typing import Optional
from database import get_cursor

router = APIRouter()

@router.get("/disponiveis")
def hoteis_disponiveis(
    cidade: Optional[str] = Query(None),
    check_in: Optional[str] = Query(None, description="YYYY-MM-DD"),
    check_out: Optional[str] = Query(None, description="YYYY-MM-DD"),
):
    sql = """
        SELECT h.id, h.name, h.city, h.stars, h.address,
               COUNT(r.id) AS quartos_disponiveis
        FROM hotels h
        JOIN rooms r ON r.hotel_id = h.id
        WHERE 1=1
    """
    params = []
    if cidade:
        sql += " AND h.city ILIKE %s"
        params.append(f"%{cidade}%")
    if check_in and check_out:
        sql += """
            AND r.id NOT IN (
                SELECT hr.room_id FROM hotel_reservations hr
                WHERE hr.status != 'cancelled'
                AND hr.check_in < %s
                AND hr.check_out > %s
            )
        """
        params += [check_out, check_in]
    sql += " GROUP BY h.id HAVING COUNT(r.id) > 0 ORDER BY h.stars DESC LIMIT 50"

    with get_cursor() as (cur, conn):
        cur.execute(sql, params)
        return cur.fetchall()
