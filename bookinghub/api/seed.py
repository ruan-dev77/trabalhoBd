"""
seed.py — Popula o banco BookingHub com dados realistas.
Requer: pip install faker psycopg2-binary
Uso:    python seed.py
"""

import os
import random
from datetime import datetime, timedelta, date
from faker import Faker
import psycopg2
from psycopg2.extras import execute_values

fake = Faker("pt_BR")
random.seed(42)
Faker.seed(42)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://booking:secret@localhost:5432/bookinghub")

# ── Dados fixos ────────────────────────────────────────────────────────────────

AIRPORTS = [
    ("GRU", "Aeroporto Internacional de Guarulhos",  "São Paulo",        "Brasil"),
    ("CGH", "Aeroporto de Congonhas",                "São Paulo",        "Brasil"),
    ("SDU", "Aeroporto Santos Dumont",               "Rio de Janeiro",   "Brasil"),
    ("GIG", "Aeroporto Internacional do Galeão",     "Rio de Janeiro",   "Brasil"),
    ("BSB", "Aeroporto Internacional de Brasília",   "Brasília",         "Brasil"),
    ("SSA", "Aeroporto Internacional de Salvador",   "Salvador",         "Brasil"),
    ("FOR", "Aeroporto Internacional de Fortaleza",  "Fortaleza",        "Brasil"),
    ("REC", "Aeroporto Internacional do Recife",     "Recife",           "Brasil"),
    ("POA", "Aeroporto Internacional de Porto Alegre","Porto Alegre",    "Brasil"),
    ("CWB", "Aeroporto Internacional de Curitiba",   "Curitiba",         "Brasil"),
    ("MAO", "Aeroporto Internacional de Manaus",     "Manaus",           "Brasil"),
    ("BEL", "Aeroporto Internacional de Belém",      "Belém",            "Brasil"),
    ("VCP", "Aeroporto Internacional de Viracopos",  "Campinas",         "Brasil"),
    ("FLN", "Aeroporto Internacional de Florianópolis","Florianópolis",  "Brasil"),
    ("MCZ", "Aeroporto Internacional de Maceió",     "Maceió",           "Brasil"),
]

AIRLINES = ["LA", "G3", "AD", "O6", "2Z"]
ROOM_TYPES = ["single", "double", "suite"]
PAYMENT_METHODS = ["credit_card", "debit_card", "pix", "boleto"]

def random_date_range(start_days=-180, end_days=180):
    base = date.today()
    start = base + timedelta(days=start_days)
    delta = (end_days - start_days)
    return start + timedelta(days=random.randint(0, delta))

def already_seeded(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM customers")
        return cur.fetchone()[0] > 0


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    if already_seeded(conn):
        print("⏭️  Banco já populado, pulando seed.")
        conn.close()
        return

    print("🌱 Iniciando seed...")

    # ── 1. Airports ───────────────────────────────────────────────────────────
    execute_values(cur,
        "INSERT INTO airports (code, name, city, country) VALUES %s ON CONFLICT DO NOTHING",
        AIRPORTS
    )
    conn.commit()
    cur.execute("SELECT id, code, city FROM airports")
    airports = cur.fetchall()  # [(id, code, city), ...]
    airport_ids = [a[0] for a in airports]
    print(f"  ✓ {len(airports)} aeroportos")

    # ── 2. Hotels (500) ───────────────────────────────────────────────────────
    hotel_rows = []
    for _ in range(500):
        airport = random.choice(airports)
        hotel_rows.append((
            fake.company() + " Hotel",
            airport[2],
            "Brasil",
            random.randint(1, 5),
            fake.street_address(),
        ))
    execute_values(cur,
        "INSERT INTO hotels (name, city, country, stars, address) VALUES %s",
        hotel_rows
    )
    conn.commit()
    cur.execute("SELECT id FROM hotels")
    hotel_ids = [r[0] for r in cur.fetchall()]
    print(f"  ✓ {len(hotel_ids)} hotéis")

    # ── 3. Rooms (3.000) ──────────────────────────────────────────────────────
    room_rows = []
    for hotel_id in hotel_ids:
        n_rooms = random.randint(3, 10)
        used_numbers = set()
        for i in range(n_rooms):
            num = str(random.randint(100, 999))
            while num in used_numbers:
                num = str(random.randint(100, 999))
            used_numbers.add(num)
            rtype = random.choice(ROOM_TYPES)
            capacity = {"single": 1, "double": 2, "suite": 4}[rtype]
            price = round(random.uniform(80, 1200), 2)
            room_rows.append((hotel_id, num, rtype, capacity, price))
    execute_values(cur,
        "INSERT INTO rooms (hotel_id, room_number, type, capacity, price_per_night) VALUES %s",
        room_rows
    )
    conn.commit()
    cur.execute("SELECT id FROM rooms")
    room_ids = [r[0] for r in cur.fetchall()]
    print(f"  ✓ {len(room_ids)} quartos")

    # ── 4. Flights (2.000) ────────────────────────────────────────────────────
    flight_rows = []
    for _ in range(2000):
        orig, dest = random.sample(airport_ids, 2)
        airline = random.choice(AIRLINES)
        number = f"{airline}{random.randint(1000,9999)}"
        dep = datetime.now() + timedelta(
            days=random.randint(-90, 180),
            hours=random.randint(0, 23),
            minutes=random.choice([0, 15, 30, 45])
        )
        arr = dep + timedelta(hours=random.randint(1, 8))
        total = random.choice([100, 120, 150, 180, 200, 220])
        avail = random.randint(0, total)
        price = round(random.uniform(150, 2500), 2)
        flight_rows.append((number, orig, dest, dep, arr, total, avail, price))
    execute_values(cur,
        """INSERT INTO flights
           (flight_number, origin_airport_id, destination_airport_id,
            departure_time, arrival_time, total_seats, available_seats, price)
           VALUES %s""",
        flight_rows
    )
    conn.commit()
    cur.execute("SELECT id, total_seats, available_seats FROM flights")
    flights = cur.fetchall()
    flight_ids = [f[0] for f in flights]
    print(f"  ✓ {len(flight_ids)} voos")

    # ── 5. Customers (2.000) ──────────────────────────────────────────────────
    customer_rows = []
    seen_emails = set()
    seen_cpfs = set()
    while len(customer_rows) < 2000:
        email = fake.unique.email()
        cpf = fake.cpf().replace(".", "").replace("-", "")
        if email in seen_emails or cpf in seen_cpfs:
            continue
        seen_emails.add(email)
        seen_cpfs.add(cpf)
        customer_rows.append((
            fake.name(), email, cpf, fake.phone_number()[:20]
        ))
    execute_values(cur,
        "INSERT INTO customers (name, email, cpf, phone) VALUES %s",
        customer_rows
    )
    conn.commit()
    cur.execute("SELECT id FROM customers")
    customer_ids = [r[0] for r in cur.fetchall()]
    print(f"  ✓ {len(customer_ids)} clientes")

    # ── 6. Flight Reservations (3.000) ────────────────────────────────────────
    fr_rows = []
    statuses = ["pending", "confirmed", "cancelled"]
    weights  = [0.2, 0.65, 0.15]
    for _ in range(3000):
        fr_rows.append((
            random.choice(customer_ids),
            random.choice(flight_ids),
            f"{random.randint(1,30)}{random.choice('ABCDEF')}",
            random.choices(statuses, weights)[0],
        ))
    execute_values(cur,
        "INSERT INTO flight_reservations (customer_id, flight_id, seat_number, status) VALUES %s",
        fr_rows
    )
    conn.commit()
    cur.execute("SELECT id, status FROM flight_reservations")
    flight_res = cur.fetchall()
    print(f"  ✓ {len(flight_res)} reservas de voo")

    # ── 7. Hotel Reservations (3.000) ─────────────────────────────────────────
    hr_rows = []
    for _ in range(3000):
        room_id = random.choice(room_ids)
        check_in = random_date_range(-60, 120)
        nights = random.randint(1, 14)
        check_out = check_in + timedelta(days=nights)
        status = random.choices(statuses, weights)[0]
        # busca preço do quarto
        cur.execute("SELECT price_per_night FROM rooms WHERE id = %s", (room_id,))
        price_night = cur.fetchone()[0]
        total = round(float(price_night) * nights, 2)
        hr_rows.append((
            random.choice(customer_ids),
            room_id, check_in, check_out, status, total
        ))
    execute_values(cur,
        """INSERT INTO hotel_reservations
           (customer_id, room_id, check_in, check_out, status, total_price)
           VALUES %s""",
        hr_rows
    )
    conn.commit()
    cur.execute("SELECT id, status FROM hotel_reservations")
    hotel_res = cur.fetchall()
    print(f"  ✓ {len(hotel_res)} reservas de hotel")

    # ── 8. Payments ───────────────────────────────────────────────────────────
    pay_rows = []
    for res_id, status in flight_res:
        if status in ("confirmed", "cancelled"):
            pay_rows.append((
                "flight", res_id,
                round(random.uniform(150, 2500), 2),
                "completed" if status == "confirmed" else "refunded",
                random.choice(PAYMENT_METHODS),
            ))
    for res_id, status in hotel_res:
        if status in ("confirmed", "cancelled"):
            pay_rows.append((
                "hotel", res_id,
                round(random.uniform(200, 8000), 2),
                "completed" if status == "confirmed" else "refunded",
                random.choice(PAYMENT_METHODS),
            ))
    execute_values(cur,
        """INSERT INTO payments
           (reservation_type, reservation_id, amount, status, payment_method)
           VALUES %s""",
        pay_rows
    )
    conn.commit()
    print(f"  ✓ {len(pay_rows)} pagamentos")

    # ── Resumo ────────────────────────────────────────────────────────────────
    cur.execute("""
        SELECT 'airports' AS t, COUNT(*) FROM airports UNION ALL
        SELECT 'hotels',        COUNT(*) FROM hotels   UNION ALL
        SELECT 'rooms',         COUNT(*) FROM rooms    UNION ALL
        SELECT 'flights',       COUNT(*) FROM flights  UNION ALL
        SELECT 'customers',     COUNT(*) FROM customers UNION ALL
        SELECT 'flight_reservations', COUNT(*) FROM flight_reservations UNION ALL
        SELECT 'hotel_reservations',  COUNT(*) FROM hotel_reservations  UNION ALL
        SELECT 'payments',      COUNT(*) FROM payments
    """)
    total = 0
    print("\n📊 Registros no banco:")
    for table, count in cur.fetchall():
        print(f"   {table:<25} {count:>6}")
        total += count
    print(f"   {'TOTAL':<25} {total:>6}")

    cur.close()
    conn.close()
    print("\n✅ Seed concluído!")

if __name__ == "__main__":
    main()
