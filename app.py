from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
from mysql.connector import IntegrityError, DatabaseError
from functools import wraps
from datetime import datetime, timedelta, date

app = Flask(__name__)
app.secret_key = "key"

# Connect to MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Juanfelix06",
    database="travel_agency"
)

cursor = db.cursor(dictionary=True)

ROLE_NAMES = {
    "business_airline": "company of airline",
    "business_hotel": "company of hotel",
    "business_car": "company of car rental"
}

def login_required(role):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session or session.get('role') != role:
                name = ROLE_NAMES.get(role, role)
                flash(f"You must be logged in as a {name} to access this page.", "warning")
                if role == 'business_airline' or role == 'business_hotel' or role == 'business_car':
                    return redirect(url_for('login_business'))
                elif role == 'customer':
                    return redirect(url_for('login_customer'))
                else:
                    return redirect(url_for('home')), 
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

@app.route('/login/customer', methods=['GET', 'POST'])
def login_customer():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor.execute("SELECT * FROM account WHERE email=%s AND password=%s AND role='customer'", (email, password))
        user = cursor.fetchone()
        if user:
            session['user_id'] = user['account_id']
            session['role'] = 'customer'
            return redirect(url_for('home'))
        else:
            flash("Invalid credentials or not a customer", "danger")
    return render_template('auth/login_customer.html')

@app.route("/signup/customer", methods=["GET", "POST"])
def signup_customer():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        name = request.form["name"]
        mobile = request.form["mobile"]
        # check if email exist
        cursor.execute("SELECT * FROM account WHERE email=%s", (email,))
        if cursor.fetchone():
            flash("Email already registered.", "danger")
            return redirect(url_for("signup_customer"))
        cursor.execute(
            "INSERT INTO account (email, password, name, mobile, role) VALUES (%s, %s, %s, %s, 'customer')",
            (email, password, name, mobile)
        )
        db.commit()
        flash("Account created successfully. Please login.", "success")
        return redirect(url_for("login_customer"))
    return render_template("auth/signup_customer.html")

@app.route('/login/business', methods=['GET', 'POST'])
def login_business():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Parameterized query with LIKE
        cursor.execute(
            "SELECT * FROM account WHERE email=%s AND password=%s AND role LIKE %s",
            (email, password, 'business_%')
        )
        user = cursor.fetchone()

        if not user:
            flash("Invalid credentials or not a business account", "danger")
            return redirect(url_for('login_business'))

        # Store user id and role in session
        session['user_id'] = user['account_id']
        session['role'] = user['role']

        # Redirect based on business type
        if user['role'] == 'business_airline':
            return redirect(url_for('airline_dashboard'))
        elif user['role'] == 'business_hotel':
            return redirect(url_for('hotel_dashboard'))
        elif user['role'] == 'business_car':
            return redirect(url_for('car_dashboard'))
        else:
            flash("Unknown business type", "danger")
            return redirect(url_for('login_business'))

    return render_template('auth/login_business.html')

@app.route("/signup/business", methods=["GET", "POST"])
def signup_business():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        business_type = request.form["business_type"]  # 'airline', 'hotel', 'car'

        cursor.execute("SELECT * FROM account WHERE email=%s", (email,))
        if cursor.fetchone():
            flash("Email already registered.", "danger")
            return redirect(url_for("signup_business"))

        role = f"business_{business_type.lower()}"
        cursor.execute(
            "INSERT INTO account (email, password, role) VALUES (%s, %s, %s)",
            (email, password, role)
        )
        db.commit()
        business_id = cursor.lastrowid

        if business_type == "airline":
            airline_name = request.form["airline_name"]
            airline_id = request.form["airline_id"].upper()  # ICAO code
            cursor.execute(
                "INSERT INTO airline (airline_id, airline_name, business_owner_id) VALUES (%s, %s, %s)",
                (airline_id, airline_name, business_id)
            )
            db.commit()
        elif business_type == "hotel":
            # TBC
            db.commit()
        elif business_type == "car":
            # TBC
            db.commit()

        flash("Business account created successfully. Please login.", "success")
        return redirect(url_for("login_business"))
    return render_template("auth/signup_business.html")

@app.route('/logout')
def logout():
    if session['role'] in ROLE_NAMES.keys():
        session.clear()
        return redirect(url_for('login_business'))
    elif session['role'] == 'customer':
        session.clear()
        return redirect(url_for('home'))

@app.route('/airline/dashboard')
@login_required('business_airline')
def airline_dashboard():
    cursor.execute(
        "SELECT airline_name FROM airline WHERE business_owner_id=%s",
        (session['user_id'],)
    )
    airline = cursor.fetchone()
    airline_name = airline['airline_name'] if airline else "Unknown Airline"

    return render_template("airline/airline_dashboard.html", airline_name=airline_name)

@app.route('/airline/dashboard/add-aircraft', methods=["GET", "POST"])
@login_required('business_airline')
def add_aircraft():
    cursor.execute(
        "SELECT airline_id, airline_name FROM airline WHERE business_owner_id = %s",
        (session['user_id'],)
    )
    airline = cursor.fetchone()
    airline_id = airline["airline_id"]
    airline_name = airline['airline_name']

    if request.method == "POST":
        model = request.form["model"]
        layout = request.form["seat_layout"].strip().upper() # Example: "3-3" or "2-4-2"
        try:
            cursor.execute(
                "INSERT INTO aircraft (airline_id, model, seat_layout) VALUES (%s, %s, %s)",
                (airline_id, model, layout)
            )
            db.commit()
            flash("Aircraft added successfully.", "success")
            return redirect(url_for("airline_dashboard"))
        except IntegrityError as e:
            if e.errno == 1062:
                flash("Aircraft with this model and seat layout already exists.", "danger")
            else:
                flash("Database error occurred.", "danger")
            return redirect(url_for("add_aircraft"))
        except DatabaseError as e:
            if e.errno == 3819:
                flash("Invalid seat layout format. Allowed layouts: 3-3, 2-4-2, etc.", "danger")
            else:
                flash("Database error occurred.", "danger")
    return render_template("airline/add_aircraft.html", airline_id=airline_id, airline_name=airline_name) 

@app.route('/airline/view-aircraft')
@login_required('business_airline')
def view_aircraft():
    cursor.execute(
        "SELECT airline_id, airline_name FROM airline WHERE business_owner_id = %s",
        (session['user_id'],)
    )
    airline = cursor.fetchone()
    airline_id = airline["airline_id"]
    airline_name = airline['airline_name']
    cursor.execute(
        "SELECT aircraft_id, model, seat_layout FROM aircraft WHERE airline_id=%s",
        (airline_id,)
    )
    aircraft_list = cursor.fetchall()
    return render_template("airline/view_aircraft.html", aircraft_list=aircraft_list, airline_name=airline_name)

@app.route('/airline/delete-aircraft/<int:aircraft_id>', methods=['POST'])
@login_required('business_airline')
def delete_aircraft(aircraft_id):
    cursor.execute(
        "SELECT airline_id FROM airline WHERE business_owner_id = %s",
        (session['user_id'],)
    )
    airline = cursor.fetchone()
    cursor.execute("DELETE FROM aircraft WHERE aircraft_id = %s AND airline_id = %s",
                   (aircraft_id, airline["airline_id"]))
    db.commit()
    flash("Aircraft removed successfully.", "success")
    return redirect(url_for('view_aircraft'))

@app.route('/airline/add-flight', methods=['GET', 'POST'])
@login_required('business_airline')
def add_flight():
    cursor.execute(
        "SELECT airline_id, airline_name FROM airline WHERE business_owner_id = %s",
        (session['user_id'],)
    )
    airline = cursor.fetchone()
    airline_name = airline['airline_name']
    airline_id = airline["airline_id"]

    if request.method == 'GET':
        cursor.execute(
            "SELECT aircraft_id, model FROM aircraft WHERE airline_id = %s",
            (airline_id,)
        )
        aircraft_list = cursor.fetchall()
        cursor.execute("SELECT airport_id, airport_name FROM airport ORDER BY airport_id")
        airport_list = cursor.fetchall()
        return render_template(
            "airline/add_flight.html",
            airline_id=airline_id,
            aircraft_list=aircraft_list,
            airport_list=airport_list,
            airline_name=airline_name
        )

    # for POST
    flight_number = request.form["flight_number"].upper()
    aircraft_id = request.form["aircraft_id"]
    dep_airport = request.form["departure_airport"]
    arr_airport = request.form["arrival_airport"]
    if dep_airport == arr_airport:
        flash("Departure and arrival airports cannot be the same.", "danger")
        return redirect(url_for("add_flight"))
    dep_terminal = request.form.get("departure_terminal") or None
    arr_terminal = request.form.get("arrival_terminal") or None
    dep_time = request.form["departure_time"]
    arr_time = request.form["arrival_time"]
    start_date = request.form["start_date"]
    direct = int(request.form.get("direct", 1))

    recurrence = int(request.form["recurrence"])

    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    dep_time = datetime.strptime(dep_time, "%H:%M").time()
    arr_time = datetime.strptime(arr_time, "%H:%M").time()

    for i in range(recurrence):
        flight_date = start_date + timedelta(days=i)

        departure_dt = datetime.combine(flight_date, dep_time)
        if arr_time <= dep_time:
            arrival_dt = datetime.combine(flight_date + timedelta(days=1), arr_time)
        else:
            arrival_dt = datetime.combine(flight_date, arr_time)
        # insert into flight
        cursor.execute("""
            INSERT INTO flight (
                airline_id, flight_number, aircraft_id,
                departure_airport_id, arrival_airport_id,
                departure_terminal, arrival_terminal,
                departure_time, arrival_time, direct
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            airline_id, flight_number, aircraft_id,
            dep_airport, arr_airport,
            dep_terminal, arr_terminal,
            departure_dt, arrival_dt, direct
        ))
        db.commit()
        # get new flight_id
        flight_id = cursor.lastrowid
        # insert fares
        fare_classes = ["ECONOMY", "BUSINESS", "FIRST"]
        for fc in fare_classes:
            price = request.form.get(f"{fc.lower()}_price")
            refundable = 1 if request.form.get(f"{fc.lower()}_refundable") else 0
            reschedulable = 1 if request.form.get(f"{fc.lower()}_reschedulable") else 0
            baggage = request.form.get(f"{fc.lower()}_baggage")
            cabin = request.form.get(f"{fc.lower()}_cabin")
            meal = 1 if request.form.get(f"{fc.lower()}_meal") else 0
            entertainment = 1 if request.form.get(f"{fc.lower()}_entertainment") else 0
            wifi = 1 if request.form.get(f"{fc.lower()}_wifi") else 0
            # insert into flight_fare
            cursor.execute("""
                INSERT INTO flight_fare (
                    flight_id, fare_class, price,
                    refundable, reschedulable,
                    baggage_kg, cabin_baggage_kg,
                    meal, entertainment, wifi
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                flight_id, fc, price,
                refundable, reschedulable,
                baggage, cabin,
                meal, entertainment, wifi
            ))
        db.commit()
    flash(f"{recurrence} recurring flight(s) created successfully.", "success")
    return redirect(url_for("airline_dashboard"))

@app.route('/airline/view-flight')
@login_required('business_airline')
def view_flight():
    # get airline
    cursor.execute("""
        SELECT airline_id, airline_name 
        FROM airline 
        WHERE business_owner_id = %s
    """, (session['user_id'],))
    airline = cursor.fetchone()
    airline_id = airline["airline_id"]
    airline_name = airline["airline_name"]

    # get flight
    cursor.execute("""
        SELECT *
        FROM flight_overview
        WHERE airline_id = %s
        ORDER BY departure_time
    """, (airline_id,))
    flights = cursor.fetchall()

    return render_template(
        "airline/view_flight.html",
        flights=flights,
        airline_name=airline_name
    )

@app.route('/airline/delete-flight/<int:flight_id>', methods=['POST'])
@login_required('business_airline')
def delete_flight(flight_id):
    cursor.execute(
        "SELECT airline_id FROM airline WHERE business_owner_id = %s",
        (session['user_id'],)
    )
    airline = cursor.fetchone()

    cursor.execute("""
        DELETE FROM flight 
        WHERE flight_id = %s AND airline_id = %s
    """, (flight_id, airline["airline_id"]))
    db.commit()
    flash("Flight deleted successfully.", "success")
    return redirect(url_for('view_flight'))

@app.route('/airline/account', methods=['GET', 'POST'])
@login_required('business_airline')
def airline_account():
    cursor.execute("""
        SELECT a.airline_id, a.airline_name, acc.email 
        FROM airline a
        JOIN account acc ON a.business_owner_id = acc.account_id
        WHERE a.business_owner_id = %s
    """, (session["user_id"],))
    data = cursor.fetchone()
    airline_name = data["airline_name"]

    if request.method == 'POST':
        airline_name = request.form["airline_name"]
        email = request.form["email"]

        # update airline table
        cursor.execute("""
            UPDATE airline
            SET airline_name = %s
            WHERE business_owner_id = %s
        """, (airline_name, session["user_id"]))

        # update account table
        cursor.execute("""
            UPDATE account
            SET email = %s
            WHERE account_id = %s
        """, (email, session["user_id"]))

        db.commit()
        flash("Account updated successfully.", "success")
        return redirect(url_for('airline_dashboard'))
    return render_template("airline/account.html", data=data, airline_name=airline_name)

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/home/account', methods=['GET', 'POST'])
@login_required('customer')
def customer_account():
    cursor.execute("""
        SELECT acc.account_id, acc.email, acc.name, acc.mobile
        FROM account acc
        WHERE account_id = %s
    """, (session["user_id"],))
    data = cursor.fetchone()

    if request.method == 'POST':
        name = request.form["name"]
        email = request.form["email"]
        mobile = request.form["mobile"]

        # update airline table
        cursor.execute("""
            UPDATE account
            SET name = %s, email = %s, mobile = %s
            WHERE account_id = %s
        """, (name, email, mobile, session["user_id"]))
        db.commit()
        flash("Account updated successfully.", "success")
        return redirect(url_for('home'))
    return render_template("customer_account.html", data=data)

@app.route('/search_airport')
@login_required('customer')
def search_airport():
    term = request.args.get("q", "").strip()
    if not term:
        return jsonify([])
    like = f"{term}%"
    wide_like = f"%{term}%"
    query = """
        SELECT airport_id, airport_name, city, country
        FROM airport
        WHERE airport_id LIKE %s
           OR airport_name LIKE %s
           OR city LIKE %s
           OR country LIKE %s
        ORDER BY 
            (airport_id LIKE %s) DESC,
            (airport_name LIKE %s) DESC,
            airport_name ASC
        LIMIT 10
    """
    cursor.execute(query, (like, wide_like, wide_like, like, wide_like, wide_like))
    return jsonify(cursor.fetchall())

def get_flights(departure_airport, arrival_airport, departure_date, seat_class):
    query = """
        SELECT 
            f.flight_id,
            f.flight_number,
            DATE(f.departure_time) as dep_date,
            DATE(f.arrival_time) as arr_date,
            TIME(f.departure_time) as dep_time,
            TIME(f.arrival_time) as arr_time,
            f.direct,
            al.airline_name,
            ac.model,
            ac.seat_layout,
            dap.airport_name AS depart_airport_name,
            aap.airport_name AS arrival_airport_name,
            dap.airport_id AS depart_airport_id,
            aap.airport_id AS arrival_airport_id,
            dap.city AS dep_city,
            aap.city AS arr_city,
            f.departure_terminal as dep_terminal,
            f.arrival_terminal AS arr_terminal,
            ff.fare_class,
            ff.price,
            ff.baggage_kg,
            ff.cabin_baggage_kg,
            ff.refundable,
            ff.reschedulable,
            ff.meal,
            ff.entertainment,
            ff.wifi,
            TIMESTAMPDIFF(
                MINUTE,
                f.departure_time - INTERVAL dap.timezone_hour HOUR - INTERVAL dap.timezone_minute MINUTE,
                f.arrival_time   - INTERVAL aap.timezone_hour HOUR - INTERVAL aap.timezone_minute MINUTE
            ) AS duration_min
        FROM flight f
        JOIN airline al ON f.airline_id = al.airline_id
        JOIN aircraft ac ON f.aircraft_id = ac.aircraft_id
        JOIN airport dap ON f.departure_airport_id = dap.airport_id
        JOIN airport aap ON f.arrival_airport_id = aap.airport_id
        JOIN flight_fare ff ON f.flight_id = ff.flight_id
        WHERE f.departure_airport_id = %s
            AND f.arrival_airport_id = %s
            AND DATE(f.departure_time) = DATE(%s)
            AND ff.fare_class = %s
        ORDER BY f.departure_time ASC
    """
    cursor.execute(query, (departure_airport, arrival_airport, departure_date, seat_class))
    return cursor.fetchall()

@app.route('/search-flights')
@login_required('customer')
def search_flights():
    # RESET trip state for a new search
    session.pop("selected_flights", None)
    session.pop("return_date", None)

    departure_airport = request.args.get("from_airport")
    arrival_airport = request.args.get("to_airport")
    departure_date = request.args.get("departure_date")
    seat_class = request.args.get("seat_class", "ECONOMY")
    return_date = request.args.get("return_date")
    passengers = request.args.get("passengers", 1)
    session["passengers"] = int(passengers)
    session.modified = True

    if return_date:
        session["return_date"] = return_date

    if not departure_airport or not arrival_airport or not departure_date:
        return "Missing required parameters", 400

    flights = get_flights(departure_airport, arrival_airport, departure_date, seat_class)
    first_flight = flights[0] if flights else None
    for f in flights:
        mins = f['duration_min'] or 0
        hours, minutes = divmod(mins, 60)
        f['duration'] = f"{hours}h {minutes}m"
    direction = request.args.get("direction", "departure")
    return render_template("air_search_results.html", flights=flights, seat_class=seat_class, first_flight=first_flight, direction=direction)

@app.route('/choose-flight', methods=['POST'])
@login_required('customer')
def choose_flight():
    flight_id = request.form.get("flight_id")
    seat_class = request.form.get("seat_class")
    direction = request.form.get("direction")  # "departure" or "return"

    # store selection in session
    if "selected_flights" not in session:
        session["selected_flights"] = {}
        session["selected_flights"][direction] = {
        "flight_id": flight_id,
        "seat_class": seat_class
    }
    session.modified = True
    if direction == "departure":
        # check if user wants a return flight
        return_date = session.get("return_date")
        if return_date:
            return redirect(url_for("search_return_flights"))
        else:
            return redirect(url_for("air_details_form"))
    else:
        return redirect(url_for("air_details_form"))
    
@app.route('/search-return-flights')
@login_required('customer')
def search_return_flights():
    return_date = session.get("return_date")
    if not return_date:
        return redirect(url_for("air_details_form"))
    
    selected_dep = session.get("selected_flights", {}).get("departure")
    if not selected_dep:
        return redirect(url_for("search_flights"))

    cursor.execute("""
        SELECT f.departure_airport_id, f.arrival_airport_id, DATE(f.departure_time) AS dep_date
        FROM flight f
        WHERE f.flight_id = %s
    """, (selected_dep["flight_id"],))
    dep_flight = cursor.fetchone()
    if not dep_flight:
        return redirect(url_for("search_flights"))

    departure_airport = dep_flight["arrival_airport_id"]
    arrival_airport = dep_flight["departure_airport_id"]
    return_date = session.get("return_date")
    seat_class = selected_dep["seat_class"]

    flights = get_flights(departure_airport, arrival_airport, return_date, seat_class)
    first_flight = flights[0] if flights else None
    for f in flights:
        mins = f['duration_min'] or 0
        hours, minutes = divmod(mins, 60)
        f['duration'] = f"{hours}h {minutes}m"
    return render_template("air_search_results.html", flights=flights, seat_class=seat_class, first_flight=first_flight, direction="return")

@app.route('/air-details-form', methods=['GET', 'POST'])
@login_required('customer')
def air_details_form():
    selected = session.get("selected_flights", {})
    dep_sel = selected.get("departure")
    ret_sel = selected.get("return")  # may be None
    if not dep_sel:
        return redirect(url_for("search_flights"))
    cursor.execute("""
        SELECT account_id, name, email, mobile
        FROM account
        WHERE account_id = %s
    """, (session["user_id"],))
    customer = cursor.fetchone()
    passengers_count = int(session.get("passengers", 1))

    # --- helper to fetch flight summary ---
    def fetch_flight(flight_id, seat_class):
        cursor.execute("""
            SELECT
                f.flight_id,
                f.flight_number,
                al.airline_name,
                DATE(f.departure_time) AS dep_date,
                TIME(f.departure_time) AS dep_time,
                DATE(f.arrival_time) AS arr_date,
                TIME(f.arrival_time) AS arr_time,
                dap.city AS dep_city,
                dap.airport_id AS dep_airport,
                aap.city AS arr_city,
                aap.airport_id AS arr_airport,
                ff.fare_class,
                ff.price
            FROM flight f
            JOIN airline al ON f.airline_id = al.airline_id
            JOIN airport dap ON f.departure_airport_id = dap.airport_id
            JOIN airport aap ON f.arrival_airport_id = aap.airport_id
            JOIN flight_fare ff ON f.flight_id = ff.flight_id
            WHERE f.flight_id = %s AND ff.fare_class = %s
        """, (flight_id, seat_class))
        return cursor.fetchone()

    dep_flight = fetch_flight(dep_sel["flight_id"], dep_sel["seat_class"])
    ret_flight = None
    if ret_sel:
        ret_flight = fetch_flight(ret_sel["flight_id"], ret_sel["seat_class"])

    if request.method == 'POST':
        # --- calculate total price ---
        total_price = dep_flight["price"]
        if ret_flight:
            total_price += ret_flight["price"]
        total_price *= passengers_count

        # --- create booking ---
        expires_at = datetime.now() + timedelta(seconds=15)
        cursor.execute("""
            INSERT INTO booking (customer_id, total_price, expires_at)
            VALUES (%s, %s, %s)
        """, (customer["account_id"], total_price, expires_at))
        booking_id = cursor.lastrowid

        # --- create departure flight_booking ---
        cursor.execute("""
            INSERT INTO flight_booking (booking_id, flight_id, fare_class)
            VALUES (%s, %s, %s)
        """, (
            booking_id,
            dep_flight["flight_id"],
            dep_sel["seat_class"]
        ))
        dep_flight_booking_id = cursor.lastrowid

        # --- insert passengers for departure ---
        passenger_data = []
        for i in range(1, passengers_count + 1):
            passenger_data.append((
                dep_flight_booking_id,
                request.form[f"title_{i}"],
                request.form[f"full_name_{i}"],
                request.form[f"dob_{i}"],
                request.form[f"nationality_{i}"]
            ))
        cursor.executemany("""
            INSERT INTO passenger
            (flight_booking_id, title, full_name, date_of_birth, nationality)
            VALUES (%s, %s, %s, %s, %s)
        """, passenger_data)

        # --- return flight (optional) ---
        if ret_flight:
            cursor.execute("""
                INSERT INTO flight_booking (booking_id, flight_id, fare_class)
                VALUES (%s, %s, %s)
            """, (
                booking_id,
                ret_flight["flight_id"],
                ret_sel["seat_class"]
            ))
            ret_flight_booking_id = cursor.lastrowid
            # reuse SAME passenger info
            passenger_data = []
            for i in range(1, passengers_count + 1):
                passenger_data.append((
                    ret_flight_booking_id,
                    request.form[f"title_{i}"],
                    request.form[f"full_name_{i}"],
                    request.form[f"dob_{i}"],
                    request.form[f"nationality_{i}"]
                ))
            cursor.executemany("""
                INSERT INTO passenger
                (flight_booking_id, title, full_name, date_of_birth, nationality)
                VALUES (%s, %s, %s, %s, %s)
            """, passenger_data)
        db.commit()
        session.pop("selected_flights", None)
        session.pop("return_date", None)
        session.pop("passengers", None)
        session["booking_id"] = booking_id
        session.modified = True
        return redirect(url_for("payment_page"))
    return render_template(
        "air_details_form.html",
        customer=customer,
        dep_flight=dep_flight,
        ret_flight=ret_flight,
        passengers_count=passengers_count
    )

@app.route('/payment', methods=['GET', 'POST'])
@login_required('customer')
def payment_page():
    booking_id = session.get("booking_id")
    cursor.execute("""
        SELECT booking_id, expires_at, status
        FROM booking
        WHERE booking_id = %s
    """, (booking_id,))
    booking = cursor.fetchone()
    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for("home"))
    
    cursor.execute("""
        SELECT
            b.booking_id,
            b.total_price,
            fb.fare_class,
            f.flight_number,
            al.airline_name,
            DATE(f.departure_time) AS dep_date,
            TIME(f.departure_time) AS dep_time,
            dap.city AS dep_city,
            dap.airport_id AS dep_airport,
            aap.city AS arr_city,
            aap.airport_id AS arr_airport
        FROM booking b
        JOIN flight_booking fb ON b.booking_id = fb.booking_id
        JOIN flight f ON fb.flight_id = f.flight_id
        JOIN airline al ON f.airline_id = al.airline_id
        JOIN airport dap ON f.departure_airport_id = dap.airport_id
        JOIN airport aap ON f.arrival_airport_id = aap.airport_id
        WHERE b.booking_id = %s
        ORDER BY f.departure_time
    """, (booking_id,))

    flights = cursor.fetchall()
    grand_total = flights[0]["total_price"] if flights else 0

    if request.method == 'POST':
        cursor.execute("""
            UPDATE booking
            SET status = 'PAID'
            WHERE booking_id = %s
        """, (booking_id,))
        db.commit()

        session.pop("booking_id", None)
        flash("Payment successful and booking confirmed. View all bookings in booking history.", "success")
        return redirect(url_for("home"))

    return render_template(
        "payment.html",
        flights=flights,
        grand_total=grand_total,
        hide_nav=True
    )

@app.route("/payment-expired")
@login_required("customer")
def payment_expired():
    booking_id = session.get("booking_id")
    if not booking_id:
        return redirect(url_for("home"))

    cursor.execute("""
        DELETE FROM booking
        WHERE booking_id = %s
        AND status = 'UNPAID'
    """, (booking_id,))
    db.commit()

    session.pop("booking_id", None)
    flash("Payment time expired. Booking has been cancelled.", "warning")
    return redirect(url_for("home"))

@app.route("/booking-history")
@login_required("customer")
def booking_history():
    cursor.execute("""
        SELECT
        b.booking_id,
        b.booking_time,
        b.status AS booking_status,
        b.total_price,
        fb.flight_booking_id,
        fb.fare_class,
        f.flight_number,
        al.airline_name,
        dap.city AS dep_city,
        aap.city AS arr_city,
        f.departure_time,
        f.arrival_time,
        ff.reschedulable,
        ff.refundable,
        br.request_type,
        br.status AS request_status,
        DATE(br.resolved_at) AS resolved_at
        FROM booking b
        LEFT JOIN flight_booking fb ON b.booking_id = fb.booking_id
        LEFT JOIN flight f ON fb.flight_id = f.flight_id
        LEFT JOIN flight_fare ff ON fb.flight_id = ff.flight_id AND fb.fare_class = ff.fare_class
        LEFT JOIN airline al ON f.airline_id = al.airline_id
        LEFT JOIN airport dap ON f.departure_airport_id = dap.airport_id
        LEFT JOIN airport aap ON f.arrival_airport_id = aap.airport_id
        LEFT JOIN (
            SELECT br1.*
            FROM booking_request br1
            JOIN (
                -- get latest request per booking
                SELECT booking_id, MAX(requested_at) AS latest
                FROM booking_request
                GROUP BY booking_id
            ) br2 ON br1.booking_id = br2.booking_id AND br1.requested_at = br2.latest
        ) br ON b.booking_id = br.booking_id
        WHERE b.customer_id = %s
        ORDER BY b.booking_time DESC, f.departure_time ASC
    """, (session["user_id"],))

    rows = cursor.fetchall()

    bookings = {}
    for r in rows:
        bid = r["booking_id"]
        if bid not in bookings:
            # Track approved/pending request type and status
            request_info = None
            if r["request_status"]:
                request_info = {"type": r["request_type"], "status": r["request_status"], "resolved_at": r["resolved_at"]}
            bookings[bid] = {
                "booking_id": bid,
                "booking_time": r["booking_time"],
                "status": r["booking_status"],
                "total_price": r["total_price"],
                "flights": [],
                "request": request_info,
                "can_reschedule": False,
                "can_refund": False
            }

        if r["flight_booking_id"]:
            bookings[bid]["flights"].append({
                "flight_number": r["flight_number"],
                "airline_name": r["airline_name"],
                "route": f"{r['dep_city']} → {r['arr_city']}",
                "departure": r["departure_time"],
                "arrival": r["arrival_time"],
                "fare_class": r["fare_class"]
            })

        # Update booking-level flags if any flight is reschedulable/refundable
        if r["reschedulable"]:
            bookings[bid]["can_reschedule"] = True
        if r["refundable"]:
            bookings[bid]["can_refund"] = True

    return render_template(
        "booking_history.html",
        bookings=bookings.values()
    )

@app.route("/booking/<int:booking_id>/request-refund", methods=["POST"])
@login_required("customer")
def request_refund(booking_id):
    cursor.execute("""
        SELECT 1 FROM booking_request
        WHERE booking_id = %s AND status = 'PENDING'
    """, (booking_id,))
    if cursor.fetchone():
        flash("You already have a pending request for this booking.", "warning")
        return redirect(url_for("booking_history"))
    
    cursor.execute("""
        INSERT INTO booking_request (booking_id, request_type)
        VALUES (%s, 'REFUND')
    """, (booking_id,))
    db.commit()

    flash("Refund request submitted. Awaiting admin approval.", "info")
    return redirect(url_for("booking_history"))

@app.route("/booking/<int:booking_id>/request-reschedule", methods=["POST"])
@login_required("customer")
def request_reschedule(booking_id):
    cursor.execute("""
        SELECT 1 FROM booking_request
        WHERE booking_id = %s AND status = 'PENDING'
    """, (booking_id,))
    if cursor.fetchone():
        flash("You already have a pending request for this booking.", "warning")
        return redirect(url_for("booking_history"))
    
    cursor.execute("""
        INSERT INTO booking_request (booking_id, request_type)
        VALUES (%s, 'RESCHEDULE')
    """, (booking_id,))
    db.commit()

    flash("Reschedule request submitted. Awaiting admin approval.", "info")
    return redirect(url_for("booking_history"))

if __name__ == '__main__':
    app.run(debug=True)