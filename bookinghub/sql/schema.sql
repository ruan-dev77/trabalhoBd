-- =============================================
-- BookingHub — Schema DDL
-- PostgreSQL 16
-- =============================================

-- Extensão para UUIDs (opcional, usamos SERIAL por simplicidade)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================
-- LIMPEZA (útil para re-executar o script)
-- =============================================
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS hotel_reservations CASCADE;
DROP TABLE IF EXISTS flight_reservations CASCADE;
DROP TABLE IF EXISTS rooms CASCADE;
DROP TABLE IF EXISTS hotels CASCADE;
DROP TABLE IF EXISTS flights CASCADE;
DROP TABLE IF EXISTS airports CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- =============================================
-- TABELAS
-- =============================================

CREATE TABLE airports (
    id          SERIAL PRIMARY KEY,
    code        CHAR(3)      NOT NULL UNIQUE,   -- IATA: GRU, CGH, SDU...
    name        VARCHAR(120) NOT NULL,
    city        VARCHAR(80)  NOT NULL,
    country     VARCHAR(60)  NOT NULL
);

CREATE TABLE hotels (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(120) NOT NULL,
    city        VARCHAR(80)  NOT NULL,
    country     VARCHAR(60)  NOT NULL,
    stars       SMALLINT     NOT NULL CHECK (stars BETWEEN 1 AND 5),
    address     VARCHAR(200) NOT NULL
);

CREATE TABLE flights (
    id                    SERIAL PRIMARY KEY,
    flight_number         VARCHAR(10)    NOT NULL,
    origin_airport_id     INT            NOT NULL REFERENCES airports(id),
    destination_airport_id INT           NOT NULL REFERENCES airports(id),
    departure_time        TIMESTAMPTZ    NOT NULL,
    arrival_time          TIMESTAMPTZ    NOT NULL,
    total_seats           SMALLINT       NOT NULL CHECK (total_seats > 0),
    available_seats       SMALLINT       NOT NULL CHECK (available_seats >= 0),
    price                 NUMERIC(10,2)  NOT NULL CHECK (price > 0),
    CHECK (available_seats <= total_seats),
    CHECK (arrival_time > departure_time),
    CHECK (origin_airport_id <> destination_airport_id)
);

CREATE TABLE rooms (
    id             SERIAL PRIMARY KEY,
    hotel_id       INT           NOT NULL REFERENCES hotels(id),
    room_number    VARCHAR(10)   NOT NULL,
    type           VARCHAR(20)   NOT NULL CHECK (type IN ('single', 'double', 'suite')),
    capacity       SMALLINT      NOT NULL CHECK (capacity > 0),
    price_per_night NUMERIC(10,2) NOT NULL CHECK (price_per_night > 0),
    UNIQUE (hotel_id, room_number)
);

CREATE TABLE customers (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(120) NOT NULL,
    email       VARCHAR(120) NOT NULL UNIQUE,
    cpf         CHAR(11)     NOT NULL UNIQUE,
    phone       VARCHAR(20),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE flight_reservations (
    id           SERIAL PRIMARY KEY,
    customer_id  INT          NOT NULL REFERENCES customers(id),
    flight_id    INT          NOT NULL REFERENCES flights(id),
    seat_number  VARCHAR(5),
    status       VARCHAR(20)  NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending', 'confirmed', 'cancelled')),
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE hotel_reservations (
    id           SERIAL PRIMARY KEY,
    customer_id  INT          NOT NULL REFERENCES customers(id),
    room_id      INT          NOT NULL REFERENCES rooms(id),
    check_in     DATE         NOT NULL,
    check_out    DATE         NOT NULL,
    status       VARCHAR(20)  NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending', 'confirmed', 'cancelled')),
    total_price  NUMERIC(10,2) NOT NULL CHECK (total_price > 0),
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CHECK (check_out > check_in)
);

CREATE TABLE payments (
    id                SERIAL PRIMARY KEY,
    reservation_type  VARCHAR(10)   NOT NULL CHECK (reservation_type IN ('flight', 'hotel')),
    reservation_id    INT           NOT NULL,
    amount            NUMERIC(10,2) NOT NULL CHECK (amount > 0),
    status            VARCHAR(20)   NOT NULL DEFAULT 'pending'
                                    CHECK (status IN ('pending', 'completed', 'refunded')),
    payment_method    VARCHAR(30)   NOT NULL CHECK (payment_method IN ('credit_card', 'debit_card', 'pix', 'boleto')),
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- =============================================
-- ÍNDICES
-- (comentários explicativos para o relatório)
-- =============================================

-- C1: Voos disponíveis — filtro por cidade de origem/destino e data
CREATE INDEX idx_airports_city ON airports(city);
CREATE INDEX idx_flights_departure_time ON flights(departure_time);
CREATE INDEX idx_flights_available_seats ON flights(available_seats) WHERE available_seats > 0;

-- C2: Taxa de ocupação — join flights x flight_reservations por status
CREATE INDEX idx_flight_reservations_flight_id ON flight_reservations(flight_id);
CREATE INDEX idx_flight_reservations_status ON flight_reservations(status);

-- C3: Quartos disponíveis — anti-join por datas (hotel_reservations)
CREATE INDEX idx_hotel_reservations_room_id ON hotel_reservations(room_id);
CREATE INDEX idx_hotel_reservations_datas ON hotel_reservations(check_in, check_out);
CREATE INDEX idx_hotel_reservations_status ON hotel_reservations(status);

-- C4: Histórico do cliente — filtro por customer_id nas duas tabelas de reserva
CREATE INDEX idx_flight_reservations_customer_id ON flight_reservations(customer_id);
CREATE INDEX idx_hotel_reservations_customer_id ON hotel_reservations(customer_id);

-- Pagamentos — lookup por reserva
CREATE INDEX idx_payments_reservation ON payments(reservation_type, reservation_id);

-- Rooms — lookup por hotel
CREATE INDEX idx_rooms_hotel_id ON rooms(hotel_id);

