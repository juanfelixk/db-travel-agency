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
    "business_accommodation": "company of accommodation"
}

@app.template_filter("datetimeformat")
def datetimeformat(value):
    if value is None:
        return ""
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.strftime("%Y-%m-%dT%H:%M")

def login_required(role):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session or session.get('role') != role:
                name = ROLE_NAMES.get(role, role)
                flash(f"You must be logged in as a {name} to access this page.", "warning")
                if role == 'business_airline' or role == 'business_accommodation':
                    return redirect(url_for('login_business'))
                elif role == 'customer':
                    return redirect(url_for('login_customer'))
                elif role == 'admin':
                    return redirect(url_for('login_admin'))
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
            "SELECT * FROM account WHERE email=%s AND password=%s AND role IN (%s, %s)",
            (email, password, 'business_airline', 'business_accommodation')
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
        elif user['role'] == 'business_accommodation':
            return redirect(url_for('accommodation_dashboard'))
        else:
            flash("Unknown business type", "danger")
            return redirect(url_for('login_business'))

    return render_template('auth/login_business.html')

@app.route("/signup/business", methods=["GET", "POST"])
def signup_business():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        business_type = request.form["business_type"]  

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

        flash("Business account created successfully. Please login.", "success")
        return redirect(url_for("login_business"))
    return render_template("auth/signup_business.html")

@app.route('/login/admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cursor.execute("SELECT * FROM account WHERE email=%s AND password=%s AND role='admin'", (email, password))
        user = cursor.fetchone()
        if user:
            session['user_id'] = user['account_id']
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid credentials or not an admin", "danger")
    return render_template('auth/login_admin.html')

@app.route('/logout')
def logout():
    if session['role'] in ROLE_NAMES.keys():
        session.clear()
        return redirect(url_for('login_business'))
    elif session['role'] == 'customer':
        session.clear()
        return redirect(url_for('home'))
    elif session['role'] == 'admin':
        session.clear()
        return redirect(url_for('login_admin'))
    
@app.route('/admin/dashboard')
@login_required('admin')
def admin_dashboard():
    return render_template('admin/admin_dashboard.html')

@app.route('/admin/flights')
@login_required('admin')
def admin_view_flight():
    cursor.execute("""
        SELECT
            f.flight_id,
            f.flight_number,
            al.airline_name,
            dep.airport_id AS dep_code,
            arr.airport_id AS arr_code,
            f.departure_time,
            f.arrival_time,
            ac.model
        FROM flight f
        JOIN airline al ON f.airline_id = al.airline_id
        JOIN airport dep ON f.departure_airport_id = dep.airport_id
        JOIN airport arr ON f.arrival_airport_id = arr.airport_id
        JOIN aircraft ac ON f.aircraft_id = ac.aircraft_id
        ORDER BY f.departure_time DESC
    """)
    flights = cursor.fetchall()

    return render_template(
        'admin/admin_view_flight.html',
        flights=flights
    )

@app.route("/admin/flights/add", methods=["GET", "POST"])
@login_required("admin")
def admin_add_flight():
    if request.method == "POST":
        start_date = datetime.strptime(request.form["start_date"], "%Y-%m-%d").date()
        recurrence = int(request.form["recurrence"])
        dep_time_raw = request.form["departure_time"]
        arr_time_raw = request.form["arrival_time"]

        for i in range(recurrence):
            flight_date = start_date + timedelta(days=i)
            dep_dt = datetime.combine(
                flight_date,
                datetime.strptime(dep_time_raw, "%H:%M").time()
            )
            arr_dt = datetime.combine(
                flight_date,
                datetime.strptime(arr_time_raw, "%H:%M").time()
            )
            # handle overnight flights
            if arr_dt <= dep_dt:
                arr_dt += timedelta(days=1)
            # ---- Insert flight ----
            cursor.execute("""
                INSERT INTO flight (
                    airline_id, flight_number, aircraft_id,
                    departure_airport_id, arrival_airport_id,
                    departure_terminal, arrival_terminal,
                    departure_time, arrival_time, direct
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                request.form["airline_id"],
                request.form["flight_number"],
                request.form["aircraft_id"],
                request.form["departure_airport_id"],
                request.form["arrival_airport_id"],
                request.form.get("departure_terminal"),
                request.form.get("arrival_terminal"),
                dep_dt,
                arr_dt,
                True
            ))
            flight_id = cursor.lastrowid
            # ---- Insert fares ----
            for cls in ["ECONOMY", "BUSINESS", "FIRST"]:
                cursor.execute("""
                    INSERT INTO flight_fare (
                        flight_id, fare_class, price,
                        refundable, reschedulable,
                        baggage_kg, cabin_baggage_kg,
                        meal, entertainment, wifi
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    flight_id,
                    cls,
                    request.form[f"price_{cls}"],
                    f"refundable_{cls}" in request.form,
                    f"reschedulable_{cls}" in request.form,
                    request.form.get(f"baggage_{cls}", 0),
                    request.form.get(f"cabin_{cls}", 7),
                    f"meal_{cls}" in request.form,
                    f"entertainment_{cls}" in request.form,
                    f"wifi_{cls}" in request.form,
                ))
        db.commit()
        flash(f"{recurrence} flight(s) created successfully.", "success")
        return redirect(url_for("admin_view_flight"))

    # ===== GET: preload dropdowns =====
    cursor.execute("SELECT airline_id, airline_name FROM airline ORDER BY airline_name")
    airlines = cursor.fetchall()

    cursor.execute("""
        SELECT a.aircraft_id, a.model, al.airline_name
        FROM aircraft a
        JOIN airline al ON a.airline_id = al.airline_id
        ORDER BY al.airline_name, a.model
    """)
    aircrafts = cursor.fetchall()

    cursor.execute("SELECT airport_id, airport_name FROM airport ORDER BY airport_id")
    airports = cursor.fetchall()

    return render_template(
        "admin/admin_add_flight.html",
        airlines=airlines,
        aircrafts=aircrafts,
        airports=airports
    )

@app.route("/admin/flights/<int:flight_id>/edit", methods=["GET", "POST"])
@login_required("admin")
def admin_edit_flight(flight_id):
    if request.method == "POST":
        try:
            cursor.execute("""
                UPDATE flight
                SET aircraft_id=%s,
                    departure_terminal=%s,
                    arrival_terminal=%s,
                    departure_time=%s,
                    arrival_time=%s
                WHERE flight_id=%s
            """, (
                request.form["aircraft_id"],
                request.form.get("departure_terminal"),
                request.form.get("arrival_terminal"),
                request.form["departure_time"],
                request.form["arrival_time"],
                flight_id
            ))

            # ---- update fares ----
            for cls in ["ECONOMY", "BUSINESS", "FIRST"]:
                cursor.execute("""
                    UPDATE flight_fare
                    SET price=%s,
                        refundable=%s,
                        reschedulable=%s,
                        baggage_kg=%s,
                        cabin_baggage_kg=%s,
                        meal=%s,
                        entertainment=%s,
                        wifi=%s
                    WHERE flight_id=%s AND fare_class=%s
                """, (
                    request.form[f"price_{cls}"],
                    f"refundable_{cls}" in request.form,
                    f"reschedulable_{cls}" in request.form,
                    request.form.get(f"baggage_{cls}", 0),
                    request.form.get(f"cabin_{cls}", 7),
                    f"meal_{cls}" in request.form,
                    f"entertainment_{cls}" in request.form,
                    f"wifi_{cls}" in request.form,
                    flight_id,
                    cls
                ))
            db.commit()
            flash("Flight updated successfully.", "success")
            return redirect(url_for("admin_view_flight"))
        except Exception as e:
            db.rollback()
            raise e

    # ---------- GET ----------
    cursor.execute("""
        SELECT f.*, al.airline_name
        FROM flight f
        JOIN airline al ON f.airline_id = al.airline_id
        WHERE f.flight_id=%s
    """, (flight_id,))
    flight = cursor.fetchone()

    cursor.execute("""
        SELECT aircraft_id, model, seat_layout
        FROM aircraft
        WHERE airline_id=%s
    """, (flight["airline_id"],))
    aircrafts = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM flight_fare
        WHERE flight_id=%s
    """, (flight_id,))
    fares = {f["fare_class"]: f for f in cursor.fetchall()}

    return render_template(
        "admin/admin_edit_flight.html",
        flight=flight,
        aircrafts=aircrafts,
        fares=fares
    )

@app.route("/admin/flights/<int:flight_id>/delete", methods=["POST", "GET"])
@login_required("admin")
def admin_delete_flight(flight_id):
    try:
        cursor.execute(
            "DELETE FROM flight WHERE flight_id = %s",
            (flight_id,)
        )
        db.commit()
        flash("Flight deleted successfully.", "success")
    except Exception:
        db.rollback()
        flash("Failed to delete flight.", "danger")
        raise
    return redirect(url_for("admin_view_flight"))

@app.route("/admin/api/aircrafts/<airline_id>")
@login_required("admin")
def admin_get_aircrafts_by_airline(airline_id):
    cursor.execute("""
        SELECT aircraft_id, model, seat_layout
        FROM aircraft
        WHERE airline_id = %s
        ORDER BY model
    """, (airline_id,))

    aircrafts = cursor.fetchall()
    return jsonify(aircrafts)

@app.route("/admin/aircraft", methods=["GET", "POST"])
@login_required("admin")
def admin_view_aircraft():
    if request.method == "POST":
        airline_id = request.form["airline_id"]
        return redirect(url_for("admin_view_aircraft_by_airline", airline_id=airline_id))

    cursor.execute("""
        SELECT airline_id, airline_name
        FROM airline
        ORDER BY airline_name
    """)
    airlines = cursor.fetchall()

    return render_template(
        "admin/admin_view_aircraft_select.html",
        airlines=airlines
    )

@app.route("/admin/aircraft/<airline_id>")
@login_required("admin")
def admin_view_aircraft_by_airline(airline_id):
    cursor.execute("""
        SELECT airline_name
        FROM airline
        WHERE airline_id = %s
    """, (airline_id,))
    airline = cursor.fetchone()

    cursor.execute("""
        SELECT aircraft_id, model, seat_layout
        FROM aircraft
        WHERE airline_id = %s
        ORDER BY model
    """, (airline_id,))
    aircrafts = cursor.fetchall()

    return render_template(
        "admin/admin_view_aircraft.html",
        airline=airline,
        airline_id=airline_id,
        aircrafts=aircrafts
    )

@app.route("/admin/aircraft/add/<airline_id>", methods=["GET", "POST"])
@login_required("admin")
def admin_add_aircraft(airline_id):
    if request.method == "POST":
        model = request.form["model"]
        seat_layout = request.form["seat_layout"]

        cursor.execute("""
            INSERT INTO aircraft (airline_id, model, seat_layout)
            VALUES (%s, %s, %s)
        """, (airline_id, model, seat_layout))

        db.commit()
        flash("Aircraft added successfully.", "success")
        return redirect(url_for("admin_view_aircraft_by_airline", airline_id=airline_id))

    cursor.execute("""
        SELECT airline_name
        FROM airline
        WHERE airline_id = %s
    """, (airline_id,))
    airline = cursor.fetchone()

    return render_template(
        "admin/admin_add_aircraft.html",
        airline=airline,
        airline_id=airline_id
    )

@app.route("/admin/aircraft/delete/<int:aircraft_id>")
@login_required("admin")
def admin_delete_aircraft(aircraft_id):
    cursor.execute("""
        SELECT airline_id
        FROM aircraft
        WHERE aircraft_id = %s
    """, (aircraft_id,))
    aircraft = cursor.fetchone()

    if not aircraft:
        flash("Aircraft not found.", "danger")
        return redirect(url_for("admin_view_aircraft"))

    cursor.execute("""
        DELETE FROM aircraft
        WHERE aircraft_id = %s
    """, (aircraft_id,))
    db.commit()

    flash("Aircraft deleted.", "success")
    return redirect(
        url_for("admin_view_aircraft_by_airline", airline_id=aircraft["airline_id"])
    )

@app.route("/admin/airports")
@login_required("admin")
def admin_view_airport():
    cursor.execute("""
        SELECT *
        FROM airport
        ORDER BY airport_id
    """)
    airports = cursor.fetchall()

    return render_template(
        "admin/admin_view_airport.html",
        airports=airports
    )

@app.route("/admin/airports/add", methods=["GET", "POST"])
@login_required("admin")
def admin_add_airport():
    if request.method == "POST":
        cursor.execute("""
            INSERT INTO airport (
                airport_id, airport_name, city, country,
                timezone_hour, timezone_minute
            )
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            request.form["airport_id"].upper(),
            request.form["airport_name"],
            request.form["city"],
            request.form["country"],
            request.form["timezone_hour"],
            request.form["timezone_minute"]
        ))

        db.commit()
        flash("Airport added successfully.", "success")
        return redirect(url_for("admin_view_airport"))
    return render_template("admin/admin_add_airport.html")

@app.route("/admin/airports/<airport_id>/delete", methods=["POST"])
@login_required("admin")
def admin_delete_airport(airport_id):
    try:
        cursor.execute(
            "DELETE FROM airport WHERE airport_id=%s",
            (airport_id,)
        )
        db.commit()
        flash("Airport deleted.", "success")
    except Exception:
        db.rollback()
        flash(
            "Cannot delete airport. It is used by flights.",
            "danger"
        )
    return redirect(url_for("admin_view_airport"))

@app.route("/admin/accounts")
@login_required("admin")
def admin_view_account():
    cursor.execute("""
        SELECT 
            a.account_id,
            a.email,
            a.name,
            a.mobile,
            a.role,
            al.airline_id,
            al.airline_name,
            p.property_id,
            p.property_name
        FROM account a
        LEFT JOIN airline al ON al.business_owner_id = a.account_id
        LEFT JOIN property p ON p.business_owner_id = a.account_id
        WHERE a.role IN ('business_airline','business_accommodation')
        ORDER BY a.account_id DESC
    """)
    accounts = cursor.fetchall()
    return render_template(
        "admin/admin_view_account.html",
        accounts=accounts
    )

@app.route("/admin/accounts/add", methods=["GET", "POST"])
@login_required("admin")
def admin_add_account():
    if request.method == "POST":
        try:
            # ---- create account ----
            cursor.execute("""
                INSERT INTO account (email, password, name, mobile, role)
                VALUES (%s,%s,%s,%s,%s)
            """, (
                request.form["email"],
                request.form["password"],  # hash later
                request.form["name"],
                request.form["mobile"],
                request.form["role"]
            ))

            account_id = cursor.lastrowid

            # ---- role-specific ----
            if request.form["role"] == "business_airline":
                cursor.execute("""
                    INSERT INTO airline (airline_id, airline_name, business_owner_id)
                    VALUES (%s,%s,%s)
                """, (
                    request.form["airline_id"],
                    request.form["airline_name"],
                    account_id
                ))

            elif request.form["role"] == "business_accommodation":
                cursor.execute("""
                    INSERT INTO property (
                        business_owner_id, property_type, property_name,
                        address, city, country, star
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, (
                    account_id,
                    request.form["property_type"],
                    request.form["property_name"],
                    request.form["address"],
                    request.form["city"],
                    request.form["country"],
                    request.form.get("star")
                ))
            db.commit()
            flash("Business account created.", "success")
            return redirect(url_for("admin_view_account"))
        except Exception as e:
            db.rollback()
            raise e
    return render_template("admin/admin_add_account.html")

@app.route("/admin/accommodations")
@login_required("admin")
def admin_view_accommodation():
    cursor.execute("""
        SELECT property_id, property_name, city, country
        FROM property
        ORDER BY property_name
    """)
    properties = cursor.fetchall()

    return render_template(
        "admin/admin_view_accommodation.html",
        properties=properties
    )

@app.route("/admin/accommodations/<int:property_id>/rooms")
@login_required("admin")
def admin_view_room_type(property_id):
    cursor.execute("""
        SELECT *
        FROM property
        WHERE property_id=%s
    """, (property_id,))
    property = cursor.fetchone()

    cursor.execute("""
        SELECT *
        FROM room_type
        WHERE property_id=%s
        ORDER BY room_name
    """, (property_id,))
    room_types = cursor.fetchall()

    return render_template(
        "admin/admin_view_room_type.html",
        property=property,
        room_types=room_types
    )

@app.route("/admin/accommodations/<int:property_id>/rooms/add", methods=["GET","POST"])
@login_required("admin")
def admin_add_room_type(property_id):
    if request.method == "POST":
        cursor.execute("""
            INSERT INTO room_type
            (property_id, room_name, max_guests, bed_type, size_sqm, total_rooms)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            property_id,
            request.form["room_name"],
            request.form["max_guests"],
            request.form.get("bed_type"),
            request.form.get("size_sqm"),
            request.form["total_rooms"]
        ))
        db.commit()

        return redirect(url_for(
            "admin_view_room_type",
            property_id=property_id
        ))

    return render_template("admin/admin_add_room_type.html", property_id=property_id)

@app.route("/admin/rooms/<int:room_type_id>/rates")
@login_required("admin")
def admin_view_room_rate(room_type_id):
    cursor.execute("""
        SELECT
            rt.room_type_id,
            rt.room_name,
            rt.property_id,
            p.property_name
        FROM room_type rt
        JOIN property p ON rt.property_id = p.property_id
        WHERE rt.room_type_id = %s
    """, (room_type_id,))
    room = cursor.fetchone()

    cursor.execute("""
        SELECT *
        FROM room_rate
        WHERE room_type_id=%s
        ORDER BY valid_from DESC
    """, (room_type_id,))
    rates = cursor.fetchall()

    return render_template(
        "admin/admin_view_room_rate.html",
        room=room,
        rates=rates
    )

@app.route("/admin/rooms/<int:room_type_id>/rates/add", methods=["GET","POST"])
@login_required("admin")
def admin_add_room_rate(room_type_id):

    if request.method == "POST":
        cursor.execute("""
            INSERT INTO room_rate
            (room_type_id, plan_name, breakfast_included,
             price_per_night, refundable, reschedulable,
             valid_from, valid_to)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            room_type_id,
            request.form["plan_name"],
            "breakfast" in request.form,
            request.form["price_per_night"],
            "refundable" in request.form,
            "reschedulable" in request.form,
            request.form["valid_from"],
            request.form["valid_to"]
        ))
        db.commit()

        return redirect(url_for(
            "admin_view_room_rate",
            room_type_id=room_type_id
        ))

    return render_template("admin/admin_add_room_rate.html", room_type_id=room_type_id)

@app.route("/admin/requests")
@login_required("admin")
def admin_view_request():
    # Fetch all booking requests
    cursor.execute("""
        SELECT br.*, b.customer_id
        FROM booking_request br
        JOIN booking b ON br.booking_id = b.booking_id
        ORDER BY br.requested_at DESC
    """)
    requests = cursor.fetchall()
    return render_template(
        "admin/admin_view_request.html",
        requests=requests
    )

@app.route("/admin/requests/<int:request_id>/resolve", methods=["POST"])
@login_required("admin")
def admin_resolve_request(request_id):
    action = request.form.get("action")  # 'APPROVED' or 'REJECTED'
    if action not in ("APPROVED", "REJECTED"):
        flash("Invalid action.", "danger")
        return redirect(url_for("admin_view_request"))
    cursor.execute("""
        UPDATE booking_request
        SET status=%s, resolved_at=NOW()
        WHERE request_id=%s
    """, (action, request_id))
    db.commit()
    flash(f"Request {action.lower()} successfully.", "success")
    return redirect(url_for("admin_view_request"))

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

# Accommodation dashboard & account management
@app.route('/accommodation/dashboard')
@login_required('business_accommodation')
def accommodation_dashboard():
    # retrieve property for this business owner (if any)
    cursor.execute("""
        SELECT property_id, property_type, property_name, city, country, star
        FROM property
        WHERE business_owner_id = %s
        LIMIT 1
    """, (session['user_id'],))
    prop = cursor.fetchone()
    accommodation_name = prop["property_name"]

    has_property = bool(prop)
    # pass property info (may be None)
    return render_template(
        "accommodation/accommodation_dashboard.html",
        property=prop,
        has_property=has_property,
        accommodation_name=accommodation_name
    )


@app.route('/accommodation/account', methods=['GET', 'POST'])
@login_required('business_accommodation')
def accommodation_account():
    # fetch existing property if exists
    cursor.execute("""
        SELECT *
        FROM property
        WHERE business_owner_id = %s
        LIMIT 1
    """, (session['user_id'],))
    prop = cursor.fetchone()
    accommodation_name = prop["property_name"]

    if request.method == 'POST':
        # gather + normalize
        property_type = (request.form.get('property_type') or '').upper()
        property_name = request.form.get('property_name', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        country = request.form.get('country', '').strip()
        check_in_time = request.form.get('check_in_time', '14:00:00')
        check_out_time = request.form.get('check_out_time', '12:00:00')

        # star only accepted if HOTEL
        star = None
        if property_type == 'HOTEL':
            star_raw = request.form.get('star')
            try:
                star = int(star_raw) if star_raw not in (None, '') else None
                if star is not None and (star < 1 or star > 5):
                    raise ValueError()
            except Exception:
                flash("Star must be an integer between 1 and 5.", "danger")
                return redirect(url_for('accommodation_account'))

        # basic required field checks
        if not property_name or not address or not city or not country or property_type not in ('HOTEL','APARTMENT','VILLA'):
            flash("Please complete all required fields.", "danger")
            return redirect(url_for('accommodation_account'))

        if prop:
            # update existing
            cursor.execute("""
                UPDATE property
                SET property_type=%s, property_name=%s, address=%s, city=%s, country=%s,
                    check_in_time=%s, check_out_time=%s, star=%s
                WHERE business_owner_id = %s
            """, (property_type, property_name, address, city, country, check_in_time, check_out_time, star, session['user_id']))
            db.commit()
            flash("Property account updated.", "success")
        else:
            # insert new
            cursor.execute("""
                INSERT INTO property
                (business_owner_id, property_type, property_name, address, city, country, check_in_time, check_out_time, star)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (session['user_id'], property_type, property_name, address, city, country, check_in_time, check_out_time, star))
            db.commit()
            flash("Property account created.", "success")

        return redirect(url_for('accommodation_dashboard'))

    # GET -> render form with existing values if present
    return render_template(
        "accommodation/account.html",
        prop=prop,
        accommodation_name=accommodation_name
    )

@app.route('/accommodation/add-room-type', methods=['GET', 'POST'])
@login_required('business_accommodation')
def add_room_type():
    # fetch property for this business owner
    cursor.execute("""
        SELECT * FROM property WHERE business_owner_id = %s
    """, (session['user_id'],))
    prop = cursor.fetchone()
    accommodation_name = prop["property_name"]
    if not prop:
        flash("Please complete your property details first.", "warning")
        return redirect(url_for('accommodation_account'))

    if request.method == 'POST':
        room_name = request.form['room_name'].strip()
        max_guests = int(request.form['max_guests'])
        bed_type = request.form.get('bed_type', '').strip()
        size_sqm = int(request.form.get('size_sqm') or 0)
        total_rooms = int(request.form['total_rooms'])

        # check duplicate
        cursor.execute("""
            SELECT * FROM room_type
            WHERE property_id = %s AND room_name = %s
        """, (prop['property_id'], room_name))
        if cursor.fetchone():
            flash("Room type already exists for this property.", "danger")
            return redirect(request.referrer or url_for('add_room_type'))

        # insert room type
        cursor.execute("""
            INSERT INTO room_type
            (property_id, room_name, max_guests, bed_type, size_sqm, total_rooms)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (prop['property_id'], room_name, max_guests, bed_type, size_sqm, total_rooms))
        db.commit()
        flash(f"Room type '{room_name}' added successfully.", "success")
        return redirect(url_for('accommodation_dashboard'))

    return render_template("accommodation/add_room_type.html", prop=prop, accommodation_name=accommodation_name)

@app.route("/accommodation/room-types")
@login_required("business_accommodation")
def view_room_type():
    # Fetch property info for the logged-in user
    cursor.execute("""
        SELECT * FROM property
        WHERE business_owner_id = %s
    """, (session["user_id"],))
    prop = cursor.fetchone()
    accommodation_name = prop["property_name"]
    if not prop:
        flash("Please complete your accommodation details first.", "warning")
        return redirect(url_for("accommodation_account"))

    # Fetch all room types for this property
    cursor.execute("""
        SELECT *
        FROM room_type
        WHERE property_id = %s
        ORDER BY room_name
    """, (prop["property_id"],))
    room_types = cursor.fetchall()

    return render_template(
        "accommodation/view_room_type.html",
        property=prop,
        room_types=room_types,
        accommodation_name=accommodation_name
    )

# --- Edit Room Type ---
@app.route("/accommodation/room-types/edit/<int:room_type_id>", methods=["GET", "POST"])
@login_required("business_accommodation")
def edit_room_type(room_type_id):
    # Fetch the room type
    cursor.execute("""
        SELECT rt.*, p.property_name
        FROM room_type rt
        JOIN property p ON rt.property_id = p.property_id
        WHERE rt.room_type_id = %s AND p.business_owner_id = %s
    """, (room_type_id, session["user_id"]))
    room = cursor.fetchone()
    if not room:
        flash("Room type not found or access denied.", "danger")
        return redirect(url_for("view_room_type"))

    if request.method == "POST":
        room_name = request.form["room_name"]
        max_guests = int(request.form["max_guests"])
        bed_type = request.form.get("bed_type")
        size_sqm = int(request.form["size_sqm"]) if request.form.get("size_sqm") else None
        total_rooms = int(request.form["total_rooms"])

        cursor.execute("""
            UPDATE room_type
            SET room_name=%s, max_guests=%s, bed_type=%s, size_sqm=%s, total_rooms=%s
            WHERE room_type_id=%s
        """, (room_name, max_guests, bed_type, size_sqm, total_rooms, room_type_id))
        db.commit()
        flash("Room type updated successfully.", "success")
        return redirect(url_for("view_room_type"))
    return render_template("accommodation/edit_room_type.html", room=room)

@app.route("/accommodation/room-types/delete/<int:room_type_id>")
@login_required("business_accommodation")
def delete_room_type(room_type_id):
    cursor.execute("""
        SELECT rt.room_type_id
        FROM room_type rt
        JOIN property p ON rt.property_id = p.property_id
        WHERE rt.room_type_id=%s AND p.business_owner_id=%s
    """, (room_type_id, session["user_id"]))
    if not cursor.fetchone():
        flash("Room type not found or access denied.", "danger")
        return redirect(url_for("view_room_type"))
    cursor.execute("DELETE FROM room_type WHERE room_type_id=%s", (room_type_id,))
    db.commit()
    flash("Room type deleted successfully.", "success")
    return redirect(url_for("view_room_type"))

@app.route('/accommodation/add-room-rate/<int:room_type_id>', methods=['GET', 'POST'])
@login_required('business_accommodation')
def add_room_rate(room_type_id):
    cursor.execute("""
        SELECT rt.room_type_id, rt.room_name, p.property_name
        FROM room_type rt
        JOIN property p ON rt.property_id = p.property_id
        WHERE rt.room_type_id = %s AND p.business_owner_id = %s
    """, (room_type_id, session['user_id']))

    room = cursor.fetchone()
    if not room:
        flash("Room type not found.", "danger")
        return redirect(url_for('view_room_type'))

    accommodation_name = room["property_name"]

    if request.method == 'POST':
        plan_name = request.form['plan_name'].strip()
        price_per_night = float(request.form['price_per_night'])
        valid_from = request.form['valid_from']
        valid_to = request.form['valid_to']

        if valid_from > valid_to:
            flash("Valid From date cannot be later than Valid To.", "danger")
            return redirect(request.url)

        try:
            cursor.execute("""
                INSERT INTO room_rate (
                    room_type_id,
                    plan_name,
                    breakfast_included,
                    price_per_night,
                    refundable,
                    reschedulable,
                    valid_from,
                    valid_to
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                room_type_id,
                plan_name,
                1 if request.form.get('breakfast_included') else 0,
                price_per_night,
                1 if request.form.get('refundable') else 0,
                1 if request.form.get('reschedulable') else 0,
                valid_from,
                valid_to
            ))
            db.commit()
        except Exception as e:
            db.rollback()
            flash("Rate plan with the same period already exists.", "danger")
            return redirect(request.url)

        flash("Room rate added successfully.", "success")
        return redirect(url_for('view_room_rate', room_type_id=room_type_id))

    return render_template(
        'accommodation/add_room_rate.html',
        room=room,
        accommodation_name=accommodation_name
    )

@app.route('/accommodation/view-room-rate/<int:room_type_id>')
@login_required('business_accommodation')
def view_room_rate(room_type_id):
    cursor.execute("""
        SELECT rr.*, rt.room_name, p.property_name
        FROM room_rate rr
        JOIN room_type rt ON rr.room_type_id = rt.room_type_id
        JOIN property p ON rt.property_id = p.property_id
        WHERE rr.room_type_id = %s AND p.business_owner_id = %s
        ORDER BY rr.plan_name
    """, (room_type_id, session['user_id']))

    rates = cursor.fetchall()
    if not rates:
        # still need room info for empty state
        cursor.execute("""
            SELECT rt.room_name, p.property_name
            FROM room_type rt
            JOIN property p ON rt.property_id = p.property_id
            WHERE rt.room_type_id = %s AND p.business_owner_id = %s
        """, (room_type_id, session['user_id']))
        meta = cursor.fetchone()
        if not meta:
            flash("Room type not found.", "danger")
            return redirect(url_for('view_room_type'))

        return render_template(
            'accommodation/view_room_rate.html',
            rates=[],
            room_type_id=room_type_id,
            room_name=meta['room_name'],
            accommodation_name=meta['property_name']
        )

    return render_template(
        'accommodation/view_room_rate.html',
        rates=rates,
        room_type_id=room_type_id,
        room_name=rates[0]['room_name'],
        accommodation_name=rates[0]['property_name']
    )

@app.route('/accommodation/edit-room-rate/<int:room_rate_id>', methods=['GET', 'POST'])
@login_required('business_accommodation')
def edit_room_rate(room_rate_id):
    cursor.execute("""
        SELECT rr.*, rt.room_name, p.property_name
        FROM room_rate rr
        JOIN room_type rt ON rr.room_type_id = rt.room_type_id
        JOIN property p ON rt.property_id = p.property_id
        WHERE rr.room_rate_id = %s AND p.business_owner_id = %s
    """, (room_rate_id, session['user_id']))

    rate = cursor.fetchone()
    if not rate:
        flash("Room rate not found.", "danger")
        return redirect(url_for('view_room_type'))

    accommodation_name = rate["property_name"]

    if request.method == 'POST':
        cursor.execute("""
            UPDATE room_rate
            SET plan_name=%s,
                price_per_night=%s,
                breakfast_included=%s,
                refundable=%s,
                reschedulable=%s
            WHERE room_rate_id=%s
        """, (
            request.form['plan_name'].strip(),
            float(request.form['price_per_night']),
            1 if request.form.get('breakfast_included') else 0,
            1 if request.form.get('refundable') else 0,
            1 if request.form.get('reschedulable') else 0,
            room_rate_id
        ))
        db.commit()
        flash("Room rate updated successfully.", "success")
        return redirect(url_for('view_room_rate', room_type_id=rate['room_type_id']))

    return render_template(
        'accommodation/edit_room_rate.html',
        rate=rate,
        accommodation_name=accommodation_name
    )

@app.route('/accommodation/delete-room-rate/<int:room_rate_id>')
@login_required('business_accommodation')
def delete_room_rate(room_rate_id):
    cursor.execute("""
        SELECT rr.room_type_id
        FROM room_rate rr
        JOIN room_type rt ON rr.room_type_id = rt.room_type_id
        JOIN property p ON rt.property_id = p.property_id
        WHERE rr.room_rate_id = %s AND p.business_owner_id = %s
    """, (room_rate_id, session['user_id']))

    row = cursor.fetchone()
    if not row:
        flash("Room rate not found.", "danger")
        return redirect(url_for('view_room_type'))

    cursor.execute("DELETE FROM room_rate WHERE room_rate_id=%s", (room_rate_id,))
    db.commit()
    flash("Room rate deleted.", "success")
    return redirect(url_for('view_room_rate', room_type_id=row['room_type_id']))

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

    # ensure selected_flights exists, then always set the direction entry
    if "selected_flights" not in session:
        session["selected_flights"] = {}
    session["selected_flights"][direction] = {
        "flight_id": int(flight_id),
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
                ff.price,
                ff.reschedulable,
                ff.refundable
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
    print("Return selection:", ret_sel)
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
    if not booking_id:
        flash("Booking not found.", "danger")
        return redirect(url_for("home"))

    # Fetch booking info
    cursor.execute("""
        SELECT booking_id, total_price, expires_at, status
        FROM booking
        WHERE booking_id = %s
    """, (booking_id,))
    booking = cursor.fetchone()
    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for("home"))

    grand_total = booking["total_price"]

    if request.method == 'POST':
        # Insert payment
        cursor.execute("""
            INSERT INTO payment (amount_paid, payment_method)
            VALUES (%s, %s)
        """, (grand_total, 'CREDIT CARD'))  # or get method from form
        payment_id = cursor.lastrowid

        # Update booking
        cursor.execute("""
            UPDATE booking
            SET status = 'PAID',
                payment_id = %s
            WHERE booking_id = %s
        """, (payment_id, booking_id))
        db.commit()

        # Clear session
        session.pop("booking_id", None)
        session.modified = True

        flash("Payment successful and booking confirmed.", "success")
        return redirect(url_for("home"))

    # Render payment page without showing flight/acc details
    return render_template(
        "payment.html",
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
    user_id = session["user_id"]

    # --- Fetch flight bookings ---
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
            ff.refundable
        FROM booking b
        LEFT JOIN flight_booking fb ON b.booking_id = fb.booking_id
        LEFT JOIN flight f ON fb.flight_id = f.flight_id
        LEFT JOIN flight_fare ff ON fb.flight_id = ff.flight_id AND fb.fare_class = ff.fare_class
        LEFT JOIN airline al ON f.airline_id = al.airline_id
        LEFT JOIN airport dap ON f.departure_airport_id = dap.airport_id
        LEFT JOIN airport aap ON f.arrival_airport_id = aap.airport_id
        WHERE b.customer_id = %s
        ORDER BY b.booking_time DESC
    """, (user_id,))
    flight_rows = cursor.fetchall()

    # --- Fetch accommodation bookings ---
    cursor.execute("""
        SELECT
            b.booking_id,
            b.booking_time,
            b.status AS booking_status,
            b.total_price,
            ab.accommodation_booking_id,
            ab.room_type_id,
            ab.room_count,
            ab.guest_count,
            ab.check_in,
            ab.check_out,
            rt.room_name,
            rr.reschedulable,
            rr.refundable,
            p.property_name,
            p.city,
            p.country
        FROM booking b
        LEFT JOIN accommodation_booking ab ON b.booking_id = ab.booking_id
        LEFT JOIN room_type rt ON ab.room_type_id = rt.room_type_id
        LEFT JOIN room_rate rr ON ab.room_rate_id = rr.room_rate_id
        LEFT JOIN property p ON rt.property_id = p.property_id
        WHERE b.customer_id = %s
        ORDER BY b.booking_time DESC
    """, (user_id,))
    acc_rows = cursor.fetchall()

    # --- Fetch booking requests ---
    cursor.execute("""
        SELECT booking_id, service_type, service_type_id, request_type, status, DATE(resolved_at) AS resolved_at
        FROM booking_request
        WHERE booking_id IN (
            SELECT booking_id FROM booking WHERE customer_id = %s
        )
    """, (user_id,))
    requests = cursor.fetchall()

    req_dict = {(r["booking_id"], r["service_type"], r["service_type_id"]): r for r in requests}

    # --- Combine bookings ---
    bookings = {}

    # Flights
    for f in flight_rows:
        # skip rows that came from LEFT JOIN but have no actual flight booking
        if f.get("flight_booking_id") is None:
            continue

        bid = f["booking_id"]
        if bid not in bookings:
            bookings[bid] = {
                "booking_id": bid,
                "booking_time": f["booking_time"],
                "status": f["booking_status"],
                "total_price": f["total_price"]
            }
        request_info = req_dict.get((bid, "FLIGHT", f["flight_booking_id"]))
        if "flights" not in bookings[bid]:
            bookings[bid]["flights"] = []
        bookings[bid]["flights"].append({
            "flight_booking_id": f["flight_booking_id"],
            "flight_number": f["flight_number"],
            "airline_name": f["airline_name"],
            "route": f"{f['dep_city']} → {f['arr_city']}" if f.get('dep_city') else None,
            "departure": f["departure_time"],
            "arrival": f["arrival_time"],
            "fare_class": f["fare_class"],
            "reschedulable": f["reschedulable"],
            "refundable": f["refundable"],
            "request": request_info
        })

    # Accommodations
    for a in acc_rows:
        # skip rows from LEFT JOIN with no actual accommodation booking
        if a.get("accommodation_booking_id") is None:
            continue

        bid = a["booking_id"]
        if bid not in bookings:
            bookings[bid] = {
                "booking_id": bid,
                "booking_time": a["booking_time"],
                "status": a["booking_status"],
                "total_price": a["total_price"]
            }
        request_info = req_dict.get((bid, "ACCOMMODATION", a["accommodation_booking_id"]))
        if "accommodations" not in bookings[bid]:
            bookings[bid]["accommodations"] = []
        bookings[bid]["accommodations"].append({
            "accommodation_booking_id": a["accommodation_booking_id"],
            "property_name": a["property_name"],
            "room_name": a["room_name"],
            "city": a["city"],
            "country": a["country"],
            "check_in": a["check_in"],
            "check_out": a["check_out"],
            "room_count": a["room_count"],
            "guest_count": a["guest_count"],
            "reschedulable": a["reschedulable"],
            "refundable": a["refundable"],
            "request": request_info
        })
    sorted_bookings = sorted(bookings.values(), key=lambda x: x["booking_id"], reverse=True)
    return render_template("booking_history.html", bookings=sorted_bookings)

@app.route("/booking/<int:booking_id>/request-refund/<int:service_id>", methods=["POST"])
@login_required("customer")
def request_refund(booking_id, service_id):
    service_type = request.form.get("service_type").upper()
    cursor.execute("""
        SELECT 1 FROM booking_request
        WHERE booking_id = %s AND service_type = %s AND service_type_id = %s AND status = 'PENDING'
    """, (booking_id, service_type, service_id))
    if cursor.fetchone():
        flash("You already have a pending request for this booking.", "warning")
        return redirect(url_for("booking_history"))
    
    cursor.execute("""
        INSERT INTO booking_request (booking_id, service_type, service_type_id, request_type)
        VALUES (%s, %s, %s, 'REFUND')
    """, (booking_id, service_type, service_id))
    db.commit()
    print(service_type)
    flash("Refund request submitted. Awaiting admin approval.", "info")
    return redirect(url_for("booking_history"))

@app.route("/booking/<int:booking_id>/request-reschedule/<int:service_id>", methods=["POST"])
@login_required("customer")
def request_reschedule(booking_id, service_id):
    service_type = request.form.get("service_type").upper()
    cursor.execute("""
        SELECT 1 FROM booking_request
        WHERE booking_id = %s AND service_type = %s AND service_type_id = %s AND status = 'PENDING'
    """, (booking_id, service_type, service_id))
    if cursor.fetchone():
        flash("You already have a pending request for this booking.", "warning")
        return redirect(url_for("booking_history"))
    
    cursor.execute("""
        INSERT INTO booking_request (booking_id, service_type, service_type_id, request_type)
        VALUES (%s, %s, %s, 'RESCHEDULE')
    """, (booking_id, service_type, service_id))
    db.commit()
    flash("Reschedule request submitted. Awaiting admin approval.", "info")
    return redirect(url_for("booking_history"))

@app.route('/search_location')
@login_required('customer')
def search_location():
    term = request.args.get("q", "").strip()
    if not term:
        return jsonify([])

    like = f"{term}%"
    wide_like = f"%{term}%"

    query = """
        SELECT
            property_id,
            property_name,
            city,
            country,
            property_type,
            rating
        FROM property
        WHERE property_name LIKE %s
           OR city LIKE %s
           OR country LIKE %s
           OR address LIKE %s
        ORDER BY
            (property_name LIKE %s) DESC,
            (city LIKE %s) DESC,
            rating DESC,
            property_name ASC
        LIMIT 10
    """
    cursor.execute(
        query,
        (wide_like, wide_like, wide_like, wide_like, like, like)
    )
    return jsonify(cursor.fetchall())

def get_accommodations(location, check_in, check_out, guests, rooms, property_type=None):
    # basic normalization
    if not location or not check_in or not check_out:
        return []

    location_term = f"%{location.strip().lower()}%"

    type_filter = ""
    type_params = []
    if property_type and property_type.upper() != "ALL":
        type_filter = "AND p.property_type = %s"
        type_params = [property_type.upper()]

    query = f"""
        SELECT
            p.property_id,
            p.property_name,
            p.property_type,
            p.city,
            p.country,
            p.rating,
            p.rating_count,
            p.star,

            rt.room_type_id,
            rt.room_name,
            rt.max_guests,
            rt.total_rooms,
            rt.bed_type,
            rt.size_sqm,

            rr.room_rate_id,
            rr.plan_name,
            rr.breakfast_included,
            rr.price_per_night,
            rr.refundable,
            rr.reschedulable,

            COALESCE(SUM(ab.room_count), 0) AS rooms_booked,
            (rt.total_rooms - COALESCE(SUM(ab.room_count), 0)) AS rooms_available

        FROM property p
        JOIN room_type rt ON p.property_id = rt.property_id
        JOIN room_rate rr ON rt.room_type_id = rr.room_type_id

        -- bookings that overlap the requested date range
        LEFT JOIN accommodation_booking ab
            ON ab.room_type_id = rr.room_type_id
            AND NOT (ab.check_out <= %s OR ab.check_in >= %s)

        WHERE
            (
              LOWER(p.city) LIKE %s
              OR LOWER(p.country) LIKE %s
              OR LOWER(p.property_name) LIKE %s
              OR LOWER(p.address) LIKE %s
            )
            AND rr.valid_from <= %s
            AND rr.valid_to >= %s
            AND rt.max_guests >= %s
            {type_filter}

        GROUP BY
            p.property_id,
            rt.room_type_id,
            rr.room_rate_id

        HAVING rooms_available >= %s

        ORDER BY
            p.rating DESC,
            rr.price_per_night ASC
    """

    # param order matches placeholders above exactly
    params = [
        check_in,            # for overlap: ab.check_out <= %s
        check_out,           # for overlap: ab.check_in >= %s
        location_term,       # LOWER(p.city) LIKE %s
        location_term,       # LOWER(p.country) LIKE %s
        location_term,       # LOWER(p.property_name) LIKE %s
        location_term,       # LOWER(p.address) LIKE %s
        check_in,            # rr.valid_from <= %s
        check_out,           # rr.valid_to >= %s
        int(guests)          # rt.max_guests >= %s
    ] + type_params + [
        int(rooms)           # HAVING rooms_available >= %s
    ]

    cursor.execute(query, params)
    return cursor.fetchall()

@app.route('/search-accommodations')
@login_required('customer')
def search_accommodations():
    session.pop("selected_rooms", None)

    location = request.args.get("location")
    check_in = request.args.get("check_in")
    check_out = request.args.get("check_out")
    guests = request.args.get("guests", 1)
    rooms = request.args.get("rooms", 1)
    property_type = request.args.get("property_type")

    # basic validation
    if not location or not check_in or not check_out:
        return "Missing required parameters", 400

    # persist counts
    session["guests"] = int(guests)
    session["rooms"] = int(rooms)
    session["check_in"] = check_in
    session["check_out"] = check_out
    session["location"] = location
    session.modified = True

    accommodations = get_accommodations(
        location=location,
        check_in=check_in,
        check_out=check_out,
        guests=int(guests),
        rooms=int(rooms),
        property_type=property_type
    )

    accommodations = get_accommodations(
    location=location,
    check_in=check_in,
    check_out=check_out,
    guests=int(guests),
    rooms=int(rooms),
    property_type=property_type
)

    # ---- INSERT HERE ----
    properties = {}

    for row in accommodations:
        pid = row["property_id"]
        rtid = row["room_type_id"]

        if pid not in properties:
            properties[pid] = {
                "property_id": pid,
                "property_name": row["property_name"],
                "property_type": row["property_type"],
                "city": row["city"],
                "country": row["country"],
                "star": row["star"],
                "rating": row["rating"],
                "rating_count": row["rating_count"],
                "rooms": {}
            }

        if rtid not in properties[pid]["rooms"]:
            properties[pid]["rooms"][rtid] = {
                "room_type_id": rtid,
                "room_name": row["room_name"],
                "max_guests": row["max_guests"],
                "rooms_available": row["rooms_available"],
                "bed_type": row["bed_type"],
                "size_sqm": row["size_sqm"],
                "rates": []
            }

        properties[pid]["rooms"][rtid]["rates"].append({
            "room_rate_id": row["room_rate_id"],
            "plan_name": row["plan_name"],
            "price_per_night": row["price_per_night"],
            "breakfast_included": row["breakfast_included"],
            "refundable": row["refundable"],
            "reschedulable": row["reschedulable"]
        })
    # ---- END INSERT ----

    check_in_dt = datetime.strptime(check_in, "%Y-%m-%d")
    check_out_dt = datetime.strptime(check_out, "%Y-%m-%d")
    stay_nights = (check_out_dt - check_in_dt).days

    # render template expecting 'accommodations' list of rows
    return render_template(
        "acc_search_results.html",
        properties=properties.values(),
        location=location,
        check_in=check_in,
        check_out=check_out,
        guests=guests,
        rooms=rooms, 
        stay_nights=stay_nights
    )

@app.route("/choose-accommodation", methods=["POST"])
@login_required("customer")
def choose_accomodation():
    room_rate_id = request.form.get("room_rate_id")
    room_type_id = request.form.get("room_type_id")

    if not room_rate_id or not room_type_id:
        return "Invalid accommodation selection", 400

    check_in = session.get("check_in")
    check_out = session.get("check_out")
    rooms = session.get("rooms")
    guests = session.get("guests")

    if not check_in or not check_out or not rooms:
        return redirect(url_for("home"))

    # ---- Recheck availability (critical) ----
    cursor.execute("""
        SELECT
        rt.total_rooms - COALESCE(SUM(ab.room_count), 0) AS rooms_available
        FROM room_type rt
        JOIN room_rate rr ON rt.room_type_id = rr.room_type_id
        LEFT JOIN accommodation_booking ab
            ON ab.room_type_id = rt.room_type_id
            AND NOT (ab.check_out <= %s OR ab.check_in >= %s)
        WHERE rr.room_rate_id = %s
        GROUP BY rt.total_rooms
    """, (check_in, check_out, room_rate_id))

    row = cursor.fetchone()
    if not row or row["rooms_available"] < int(rooms):
        flash("Selected room is no longer available", "danger")
        return redirect(request.referrer)

    # ---- Store selection in session ----
    session["selected_accommodation"] = {
        "room_rate_id": int(room_rate_id),
        "room_type_id": int(room_type_id),
        "check_in": check_in,
        "check_out": check_out,
        "rooms": int(rooms),
        "guests": int(guests)
    }
    session.modified = True

    return redirect(url_for("acc_details_form"))

@app.route("/accommodation-details-form", methods=["GET", "POST"])
@login_required("customer")
def acc_details_form():
    # Expect selection stored earlier
    data = session.get("selected_accommodation")
    if not data:
        return redirect(url_for("search_accommodations"))

    # Basic fields from session/selection
    room_rate_id = int(data["room_rate_id"])
    room_type_id = int(data["room_type_id"])
    check_in = data["check_in"]
    check_out = data["check_out"]
    rooms = int(data["rooms"])
    guests = int(data.get("guests", session.get("guests", 1)))

    # fetch logged-in customer contact
    cursor.execute("""
        SELECT account_id, name, email, mobile
        FROM account
        WHERE account_id = %s
    """, (session["user_id"],))
    customer = cursor.fetchone()
    if not customer:
        flash("Customer not found.", "danger")
        return redirect(url_for("home"))

    # fetch room / rate / property summary
    cursor.execute("""
        SELECT
            p.property_id,
            p.property_name,
            p.city,
            p.country,
            p.star,
            p.check_in_time,
            p.check_out_time,
            rt.room_type_id,
            rt.room_name,
            rt.max_guests,
            rr.room_rate_id,
            rr.plan_name,
            rr.breakfast_included,
            rr.price_per_night,
            rr.refundable,
            rr.reschedulable
        FROM room_rate rr
        JOIN room_type rt ON rr.room_type_id = rt.room_type_id
        JOIN property p ON rt.property_id = p.property_id
        WHERE rr.room_rate_id = %s
    """, (room_rate_id,))
    info = cursor.fetchone()
    if not info:
        flash("Selected accommodation not found.", "danger")
        return redirect(url_for("search_accommodations"))

    # compute nights and total price
    check_in_dt = datetime.strptime(check_in, "%Y-%m-%d")
    check_out_dt = datetime.strptime(check_out, "%Y-%m-%d")
    nights = (check_out_dt - check_in_dt).days
    total_price = info["price_per_night"] * nights * rooms

    if request.method == "POST":
        # Re-check availability: rooms available for this room_type in the date range
        cursor.execute("""
            SELECT rt.total_rooms - COALESCE(SUM(ab.room_count),0) AS rooms_available
            FROM room_type rt
            JOIN room_rate rr ON rt.room_type_id = rr.room_type_id
            LEFT JOIN accommodation_booking ab
                ON ab.room_type_id = rt.room_type_id
                AND NOT (ab.check_out <= %s OR ab.check_in >= %s)
            WHERE rr.room_rate_id = %s
            GROUP BY rt.room_type_id, rt.total_rooms
        """, (check_in, check_out, room_rate_id))
        row = cursor.fetchone()
        if not row or row["rooms_available"] < rooms:
            flash("Selected room is no longer available for the requested dates.", "danger")
            return redirect(request.referrer or url_for("search_accommodations"))

        # --- create booking ---
        expires_at = datetime.now() + timedelta(seconds=15)
        cursor.execute("""
            INSERT INTO booking (customer_id, total_price, expires_at)
            VALUES (%s, %s, %s)
        """, (customer["account_id"], total_price, expires_at))
        booking_id = cursor.lastrowid

        # --- create accommodation_booking ---
        cursor.execute("""
            INSERT INTO accommodation_booking
            (booking_id, room_rate_id, room_type_id, room_count, check_in, check_out, guest_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (booking_id, room_rate_id, room_type_id, rooms, check_in, check_out, guests))
        accommodation_booking_id = cursor.lastrowid

        guest_full_name = request.form.get("guest_full_name", "").strip()
        if not guest_full_name:
            flash("Guest name is required.", "danger")
            return redirect(request.referrer)

        cursor.execute("""
            INSERT INTO accommodation_guest (accommodation_booking_id, full_name)
            VALUES (%s, %s)
        """, (accommodation_booking_id, guest_full_name))

        db.commit()

        # clear session search/selection state (mirror flight logic)
        session.pop("selected_accommodation", None)
        session.pop("check_in", None)
        session.pop("check_out", None)
        session.pop("rooms", None)
        session.pop("guests", None)
        session["booking_id"] = booking_id
        session.modified = True

        return redirect(url_for("payment_page"))

    # GET -> render details form
    return render_template(
        "acc_details_form.html",
        customer=customer,
        info=info,
        data=data,
        nights=nights,
        total_price=total_price,
        rooms=rooms,
        guests=guests
    )

if __name__ == '__main__':
    app.run(debug=True)