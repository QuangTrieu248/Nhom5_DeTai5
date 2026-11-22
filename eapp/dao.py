from datetime import datetime

from eapp.models import Airport, Airplane, User, db
import cloudinary.uploader
import hashlib
from eapp.models import (
    Airline,
    Airplane,
    Airport,
    AirportFlightRoute,
    AirportFlightSegment,
    BoardingPass,
    Flight,
    FlightRoute,
    FlightSegment,
    Regulation,
    Seat,
    Ticket,
    User,
    db, AirportRole, app
)
from flask import render_template, request
from sqlalchemy import func
from sqlalchemy.orm import aliased



def load_airports():
    return Airport.query.all()


def count_airplane():
    return Airplane.query.count()


def get_user_by_id(user_id):
    return User.query.get(int(user_id))


def get_user_by_username(username):
    if not username:
        return None
    return User.query.filter(User.username.__eq__(username.strip())).first()


def get_phone_number(phone):
    if not phone:
        return None
    return User.query.filter(User.phone.__eq__(phone.strip())).first()


def check_login(username, password):
    if not username or not password:
        return None
    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())
    return User.query.filter(
        User.username.__eq__(username.strip()),
        User.password.__eq__(password)
    ).first()


def add_user(name, username, password, phone=None, avatar=None):
    password = hashlib.md5(password.strip().encode('utf-8')).hexdigest()
    u = User(
        name=name.strip(),
        username=username.strip(),
        phone=phone.strip() if phone else None,
        password=password
    )
    if avatar and avatar.filename != '':
        res = cloudinary.uploader.upload(avatar)
        u.avatar = res.get('secure_url')

    db.session.add(u)
    db.session.commit()




#======= TRUY VAN CHUYEN BAY THEO FORM TIM KIEM=========

#### tim chuyen bay
@app.route("/")
def index():
    airports = Airport.query.all()
    return render_template("homepage.html", airports=airports)


def query_flights_by_route(dep_id, arr_id, date_str):
    dep_route = aliased(AirportFlightRoute)
    arr_route = aliased(AirportFlightRoute)

    query = (
        db.session.query(
            Flight.id.label("id"),
            Airline.name.label("airline_name"),
            Flight.flight_code.label("flight_code"),
            func.min(FlightSegment.departure_time).label("departure_time"),
            func.max(FlightSegment.arrival_time).label("arrival_time"),
            Flight.base_price.label("base_price"),
            func.count(FlightSegment.id).label("segment_count")
        )
        .join(Airline, Flight.airline_id == Airline.id)
        .join(FlightSegment, Flight.id == FlightSegment.flight_id)
        .join(FlightRoute, Flight.flight_route_id == FlightRoute.id)
        # Chỉ lọc sân bay ĐI và ĐẾN của toàn tuyến (FlightRoute)
        .join(
            dep_route,
            (dep_route.flight_route_id == FlightRoute.id) &
            (dep_route.role == AirportRole.DEPARTURE)
        )
        .join(
            arr_route,
            (arr_route.flight_route_id == FlightRoute.id) &
            (arr_route.role == AirportRole.ARRIVAL)
        )
        .filter(
            dep_route.airport_id == dep_id,
            arr_route.airport_id == arr_id
        )
        .group_by(Flight.id, Airline.name, Flight.flight_code, Flight.base_price)
    )

    if date_str:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        query = query.having(func.date(func.min(FlightSegment.departure_time)) == target_date)

    return query.order_by(func.min(FlightSegment.departure_time).asc()).all()

