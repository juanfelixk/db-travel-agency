CREATE DATABASE IF NOT EXISTS travel_agency;
USE travel_agency;
-- DROP DATABASE travel_agency;

CREATE TABLE account (
    account_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    mobile VARCHAR(20),
    role ENUM('customer', 'business_airline', 'business_hotel', 'business_car', 'admin') NOT NULL,
    PRIMARY KEY (account_id),
    UNIQUE KEY uq_account_email (email)
);
INSERT INTO account (email, password, name, mobile, role)
VALUES
('juan@customer.com', 'juan', 'Juan Felix Kusnadi', '082249449937', 'customer'),
('klm@klm.com', 'klm', NULL, NULL, 'business_airline'),
('gia@gia.com', 'gia', NULL, NULL, 'business_airline');

/* ===========================================================
   AIRLINE (Owned by business accounts)
=========================================================== */
CREATE TABLE airline (
    airline_id CHAR(3) NOT NULL, -- ICAO code
    airline_name VARCHAR(255) NOT NULL,
    business_owner_id INT UNSIGNED NOT NULL, -- account that owns this airline
    PRIMARY KEY (airline_id),
    FOREIGN KEY (business_owner_id) REFERENCES account(account_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);
INSERT INTO airline (airline_id, airline_name, business_owner_id)
VALUES
('KLM', 'KLM Royal Dutch Airlines', 2),
('GIA', 'Garuda Indonesia', 3);

/* ===========================================================
   AIRPORT
=========================================================== */
CREATE TABLE airport (
    airport_id CHAR(3) NOT NULL, -- IATA code
    airport_name VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL,
    timezone_hour TINYINT NOT NULL,
    timezone_minute TINYINT NOT NULL,
    PRIMARY KEY (airport_id),
    CHECK (timezone_hour BETWEEN -12 AND 14),
    CHECK (timezone_minute IN (0, 30, 45))
);
INSERT INTO airport (airport_id, airport_name, city, country, timezone_hour, timezone_minute)
VALUES
('CGK', 'Soekarno-Hatta International', 'Jakarta', 'Indonesia',7, 0),
('DPS', 'Ngurah Rai International', 'Denpasar', 'Indonesia', 8, 0),
('KUL', 'Kuala Lumpur International', 'Kuala Lumpur', 'Malaysia', 8, 0);

/* ===========================================================
   AIRCRAFT (Simplified for travel agency)
=========================================================== */
CREATE TABLE aircraft (
    aircraft_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    airline_id CHAR(3) NOT NULL,
    model VARCHAR(100) NOT NULL,
    seat_layout VARCHAR(10) NOT NULL, -- e.g., '3-3' or '2-4-2'
    CHECK (
    -- One segment: A (1–3)
    seat_layout REGEXP '^[1-3]$'
    OR 
    -- Two segments: A-B  (1–3)-(1–4)
    seat_layout REGEXP '^[1-3]-[1-4]$'
    OR 
    -- Three segments: A-B-C (1–3)-(1–4)-(1–3)
    seat_layout REGEXP '^[1-3]-[1-4]-[1-3]$'),
    PRIMARY KEY (aircraft_id),
    UNIQUE KEY uq_aircraft (airline_id, model, seat_layout),
    FOREIGN KEY (airline_id) REFERENCES airline(airline_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);
INSERT INTO aircraft (airline_id, model, seat_layout)
VALUES
('KLM', 'Boeing 737-800', '3-3'),
('KLM', 'Airbus 320-200', '3-3');

/* ===========================================================
   FLIGHT (One actual flight = one row)
=========================================================== */
CREATE TABLE flight (
    flight_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    airline_id CHAR(3) NOT NULL,
    flight_number VARCHAR(10) NOT NULL, -- e.g., GA432
    aircraft_id INT UNSIGNED NOT NULL,
    departure_airport_id CHAR(3) NOT NULL,
    arrival_airport_id CHAR(3) NOT NULL,
    departure_terminal VARCHAR(50),
    arrival_terminal VARCHAR(50),
    departure_time DATETIME NOT NULL,
    arrival_time DATETIME NOT NULL,
    direct BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (flight_id),
    FOREIGN KEY (airline_id) REFERENCES airline(airline_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (aircraft_id) REFERENCES aircraft(aircraft_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (departure_airport_id) REFERENCES airport(airport_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (arrival_airport_id) REFERENCES airport(airport_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_flight_route (departure_airport_id, arrival_airport_id),
    INDEX idx_flight_time (departure_time)
);
INSERT INTO flight (
    airline_id, flight_number, aircraft_id,
    departure_airport_id, arrival_airport_id, departure_terminal, arrival_terminal,
    departure_time, arrival_time, direct
)
VALUES
('KLM', 'KL 390', 1, 'CGK', 'KUL', 'Terminal 3', 'Terminal 2', '2025-01-15 08:00:00', '2025-01-15 10:40:00', TRUE),
('KLM', 'KL 391', 2, 'KUL', 'CGK', 'Terminal 2', 'Terminal 3', '2025-01-16 09:30:00', '2025-01-16 13:15:00', TRUE);

/* ===========================================================
   FLIGHT FARES (Three classes, each single price)
=========================================================== */
CREATE TABLE flight_fare (
    flight_id INT UNSIGNED NOT NULL,
    fare_class ENUM('ECONOMY', 'BUSINESS', 'FIRST') NOT NULL,
    price DECIMAL(12,2) NOT NULL,
    refundable BOOLEAN DEFAULT FALSE,
    reschedulable BOOLEAN DEFAULT FALSE,
    baggage_kg INT NOT NULL DEFAULT 0,
    cabin_baggage_kg INT NOT NULL DEFAULT 7,
    meal BOOLEAN DEFAULT FALSE,
    entertainment BOOLEAN DEFAULT FALSE,
    wifi BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (flight_id, fare_class),
    FOREIGN KEY (flight_id) REFERENCES flight(flight_id)
        ON UPDATE CASCADE ON DELETE CASCADE
);
INSERT INTO flight_fare (
    flight_id, fare_class, price, refundable, reschedulable,
    baggage_kg, cabin_baggage_kg, meal, entertainment, wifi
)
VALUES
(1, 'ECONOMY', 850000, TRUE, TRUE, 20, 7, TRUE, TRUE, FALSE),
(1, 'BUSINESS', 2500000, TRUE, TRUE, 35, 10, TRUE, TRUE, TRUE),
(1, 'FIRST', 4500000, TRUE, TRUE, 50, 15, TRUE, TRUE, TRUE);
INSERT INTO flight_fare (
    flight_id, fare_class, price, refundable, reschedulable,
    baggage_kg, cabin_baggage_kg, meal, entertainment, wifi
)
VALUES
(2, 'ECONOMY', 600000, FALSE, FALSE, 15, 7, FALSE, FALSE, FALSE),
(2, 'BUSINESS', 1500000, TRUE, TRUE, 25, 7, TRUE, FALSE, FALSE),
(2, 'FIRST', 3000000, TRUE, TRUE, 40, 10, TRUE, TRUE, FALSE);

CREATE TABLE payment (
    payment_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    payment_method VARCHAR(50) NOT NULL,
    amount_paid DECIMAL(12,2) NOT NULL,
    payment_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (payment_id)
);

/* ===========================================================
   BOOKING (customer makes a booking)
=========================================================== */
CREATE TABLE booking (
	booking_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    customer_id INT UNSIGNED NOT NULL, -- account_id for customer
    booking_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status ENUM('UNPAID', 'PAID', 'CANCELLED') NOT NULL DEFAULT 'UNPAID',
    total_price DECIMAL(12,2) NOT NULL,
    payment_id INT UNSIGNED,
    expires_at DATETIME NOT NULL,
    PRIMARY KEY (booking_id),
    UNIQUE KEY uq_booking_payment (payment_id),
    FOREIGN KEY (customer_id) REFERENCES account(account_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
	FOREIGN KEY (payment_id) REFERENCES payment(payment_id)
		ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE TABLE flight_booking (
    flight_booking_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    booking_id INT UNSIGNED NOT NULL,
    flight_id INT UNSIGNED NOT NULL,
    fare_class ENUM('ECONOMY', 'BUSINESS', 'FIRST') NOT NULL,
    PRIMARY KEY (flight_booking_id),
    FOREIGN KEY (booking_id) REFERENCES booking(booking_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
	FOREIGN KEY (flight_id) REFERENCES flight(flight_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

/* ===========================================================
   PASSENGERS (Temporary, only inside booking)
=========================================================== */
CREATE TABLE passenger (
    passenger_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    flight_booking_id INT UNSIGNED NOT NULL,
    title ENUM('MR','MS','MRS') NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    date_of_birth DATE NOT NULL,
    nationality VARCHAR(100) NOT NULL,
    PRIMARY KEY (passenger_id),
    FOREIGN KEY (flight_booking_id) REFERENCES flight_booking(flight_booking_id)
        ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE booking_request (
    request_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    booking_id INT UNSIGNED NOT NULL,
    request_type ENUM('REFUND', 'RESCHEDULE') NOT NULL,
    reason TEXT,
    status ENUM('PENDING', 'APPROVED', 'REJECTED') NOT NULL DEFAULT 'PENDING',
    requested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME NULL,
    CONSTRAINT fk_booking_request_booking
        FOREIGN KEY (booking_id)
        REFERENCES booking(booking_id)
        ON DELETE CASCADE,
    CONSTRAINT uq_booking_pending_request
        UNIQUE (booking_id, status)
);

CREATE VIEW flight_overview AS
SELECT
    f.flight_id,
    f.airline_id,
    f.flight_number,
    a.model AS aircraft_model,
    dap.airport_id AS departure_airport_id,
    dap.airport_name AS departure_airport_name,
    aap.airport_id AS arrival_airport_id,
    aap.airport_name AS arrival_airport_name,
    f.departure_time,
    f.arrival_time,
    f.direct
FROM flight f
JOIN aircraft a ON f.aircraft_id = a.aircraft_id
JOIN airport dap ON f.departure_airport_id = dap.airport_id
JOIN airport aap ON f.arrival_airport_id = aap.airport_id;

SELECT * FROM flight;
SELECT * FROM flight_fare;
SELECT * FROM booking;
SELECT * FROM flight_booking;
SELECT * FROM passenger;
SELECT * FROM payment;
SELECT * FROM booking_request;
UPDATE booking_request SET status = 'APPROVED', resolved_at = '2025-12-13 20.55.00' WHERE request_id = 7;
DELETE FROM booking_request WHERE request_id IN (1,2,3,4,5,6,7,8,9,10);