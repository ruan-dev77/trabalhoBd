"""
analise_planos.py — Executa EXPLAIN (ANALYZE, BUFFERS) nas 4 consultas
e mede o tempo com e sem índices.

Uso:
    python analise_planos.py
"""

import os
import time
import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://booking:secret@localhost:5432/bookinghub")

# ── Consultas ─────────────────────────────────────────────────────────────────

CONSULTAS = {
    "C1 — Voos disponíveis com filtro": """
        SELECT f.id, f.flight_number, f.departure_time, f.arrival_time,
               f.available_seats, f.price,
               a1.code AS origin, a2.code AS destination
        FROM flights f
        JOIN airports a1 ON a1.id = f.origin_airport_id
        JOIN airports a2 ON a2.id = f.destination_airport_id
        WHERE a1.city = 'São Paulo'
          AND a2.city = 'Rio de Janeiro'
          AND f.departure_time BETWEEN NOW() - INTERVAL '90 days' AND NOW() + INTERVAL '180 days'
          AND f.available_seats > 0
        ORDER BY f.departure_time
    """,

    "C2 — Taxa de ocupação por voo": """
        SELECT f.flight_number,
               COUNT(fr.id) AS total_reservas,
               f.total_seats,
               ROUND(COUNT(fr.id)::numeric / f.total_seats * 100, 2) AS ocupacao_pct
        FROM flights f
        LEFT JOIN flight_reservations fr ON fr.flight_id = f.id
            AND fr.status = 'confirmed'
        WHERE f.departure_time >= NOW() - INTERVAL '30 days'
        GROUP BY f.id, f.flight_number, f.total_seats
        ORDER BY ocupacao_pct DESC
        LIMIT 20
    """,

    "C3 — Quartos disponíveis sem conflito de datas": """
        SELECT r.id, r.room_number, r.type, r.price_per_night
        FROM rooms r
        WHERE r.hotel_id = 1
          AND r.id NOT IN (
              SELECT hr.room_id FROM hotel_reservations hr
              WHERE hr.status != 'cancelled'
                AND hr.check_in  < '2026-12-31'
                AND hr.check_out > '2026-12-20'
          )
    """,

    "C4 — Histórico completo do cliente": """
        SELECT 'voo' AS tipo,
               fr.id AS reserva_id,
               f.flight_number AS descricao,
               f.departure_time AS data,
               fr.status,
               p.amount
        FROM flight_reservations fr
        JOIN flights f ON f.id = fr.flight_id
        LEFT JOIN payments p ON p.reservation_id = fr.id
            AND p.reservation_type = 'flight'
        WHERE fr.customer_id = 1
        UNION ALL
        SELECT 'hotel', hr.id, h.name, hr.check_in::timestamptz,
               hr.status, p.amount
        FROM hotel_reservations hr
        JOIN rooms r ON r.id = hr.room_id
        JOIN hotels h ON h.id = r.hotel_id
        LEFT JOIN payments p ON p.reservation_id = hr.id
            AND p.reservation_type = 'hotel'
        WHERE hr.customer_id = 1
        ORDER BY data DESC
    """,
}

# ── Índices ───────────────────────────────────────────────────────────────────

INDICES = [
    "idx_airports_city",
    "idx_flights_departure_time",
    "idx_flights_available_seats",
    "idx_flight_reservations_flight_id",
    "idx_flight_reservations_status",
    "idx_hotel_reservations_room_id",
    "idx_hotel_reservations_datas",
    "idx_hotel_reservations_status",
    "idx_flight_reservations_customer_id",
    "idx_hotel_reservations_customer_id",
    "idx_payments_reservation",
    "idx_rooms_hotel_id",
]

def executar_explain(cur, sql):
    explain = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {sql}"
    cur.execute(explain)
    return "\n".join(row[0] for row in cur.fetchall())

def medir_tempo(cur, sql, repeticoes=5):
    tempos = []
    for _ in range(repeticoes):
        inicio = time.perf_counter()
        cur.execute(sql)
        cur.fetchall()
        tempos.append((time.perf_counter() - inicio) * 1000)
    return sum(tempos) / len(tempos)

def desabilitar_indices(cur):
    cur.execute("SET enable_indexscan = off")
    cur.execute("SET enable_bitmapscan = off")

def habilitar_indices(cur):
    cur.execute("SET enable_indexscan = on")
    cur.execute("SET enable_bitmapscan = on")

def main():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    resultado = []
    separador = "=" * 80

    print(separador)
    print("ANÁLISE DE PLANOS DE EXECUÇÃO — BookingHub")
    print(separador)

    for nome, sql in CONSULTAS.items():
        print(f"\n{'─' * 80}")
        print(f"📋 {nome}")
        print('─' * 80)

        # ── COM índices ──
        habilitar_indices(cur)
        tempo_com = medir_tempo(cur, sql)
        plano_com = executar_explain(cur, sql)

        # ── SEM índices ──
        desabilitar_indices(cur)
        tempo_sem = medir_tempo(cur, sql)
        plano_sem = executar_explain(cur, sql)

        habilitar_indices(cur)

        ganho = ((tempo_sem - tempo_com) / tempo_sem * 100) if tempo_sem > 0 else 0

        print(f"\n⚡ Tempo COM índices:  {tempo_com:.2f} ms")
        print(f"🐢 Tempo SEM índices:  {tempo_sem:.2f} ms")
        print(f"📈 Ganho de performance: {ganho:.1f}%")

        print(f"\n── Plano COM índices ──")
        print(plano_com)
        print(f"\n── Plano SEM índices ──")
        print(plano_sem)

        resultado.append({
            "consulta": nome,
            "tempo_com_indice_ms": round(tempo_com, 2),
            "tempo_sem_indice_ms": round(tempo_sem, 2),
            "ganho_pct": round(ganho, 1),
        })

    # ── Tabela comparativa ────────────────────────────────────────────────────
    print(f"\n{separador}")
    print("TABELA COMPARATIVA DE TEMPOS")
    print(separador)
    print(f"{'Consulta':<45} {'Com índice':>12} {'Sem índice':>12} {'Ganho':>8}")
    print("─" * 80)
    for r in resultado:
        nome_curto = r["consulta"][:44]
        print(f"{nome_curto:<45} {r['tempo_com_indice_ms']:>10.2f}ms {r['tempo_sem_indice_ms']:>10.2f}ms {r['ganho_pct']:>7.1f}%")

    cur.close()
    conn.close()
    print(f"\n✅ Análise concluída!")

if __name__ == "__main__":
    main()
