from datetime import datetime
from decimal import Decimal, InvalidOperation

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


#======= LẬP LỊCH CHUYẾN BAY (ISSUE #38) =========

def get_schedule_form_data():
    reg = Regulation.query.first()
    airports = Airport.query.order_by(Airport.name.asc()).all()
    airlines = Airline.query.order_by(Airline.name.asc()).all()
    airplanes = Airplane.query.all()
    routes = FlightRoute.query.all()

    airport_map = {a.id: a.name for a in airports}

    routes_data = []
    for r in routes:
        dep_afr = next((x for x in r.airport_relation if x.role == AirportRole.DEPARTURE), None)
        arr_afr = next((x for x in r.airport_relation if x.role == AirportRole.ARRIVAL), None)
        routes_data.append({
            "id": r.id,
            "name": r.name,
            "airline_id": r.airline_id,
            "dep_id": dep_afr.airport_id if dep_afr else None,
            "dep_name": airport_map.get(dep_afr.airport_id, "") if dep_afr else "",
            "arr_id": arr_afr.airport_id if arr_afr else None,
            "arr_name": airport_map.get(arr_afr.airport_id, "") if arr_afr else ""
        })

    airplanes_data = [
        {
            "id": p.id,
            "label": f"Máy bay #{p.id} ({p.number_seat} ghế)",
            "airline_id": p.airline_id
        }
        for p in airplanes
    ]

    flights = Flight.query.order_by(Flight.id.desc()).all()
    scheduled_flights = []
    for f in flights:
        segs = sorted(f.segments_relation, key=lambda s: s.sequence)
        seg_details = []
        for s in segs:
            dep_s = next((x for x in s.airport_relation if x.role == AirportRole.DEPARTURE), None)
            arr_s = next((x for x in s.airport_relation if x.role == AirportRole.ARRIVAL), None)
            seg_details.append({
                "sequence": s.sequence,
                "dep_name": airport_map.get(dep_s.airport_id, "N/A") if dep_s else "N/A",
                "arr_name": airport_map.get(arr_s.airport_id, "N/A") if arr_s else "N/A",
                "departure_time": s.departure_time,
                "arrival_time": s.arrival_time,
                "airplane": f"#{s.airplane_id} ({s.airplane.number_seat} ghế)" if s.airplane else "N/A"
            })
        scheduled_flights.append({
            "id": f.id,
            "flight_code": f.flight_code,
            "airline_name": f.airline.name if f.airline else "N/A",
            "route_name": f.flight_route.name if f.flight_route else "N/A",
            "base_price": f.base_price,
            "segments": seg_details
        })

    return {
        "reg": reg,
        "airports": airports,
        "airlines": airlines,
        "routes_data": routes_data,
        "airplanes_data": airplanes_data,
        "scheduled_flights": scheduled_flights
    }


def create_scheduled_flight(flight_code, airline_id, flight_route_id, base_price_raw, segments_input):
    """
    Kiểm tra quy định (Regulation) và lưu Flight + FlightSegment + AirportFlightSegment.
    Trả về (True, 'Thông báo thành công') hoặc (False, 'Thông báo lỗi').
    """
    flight_code = (flight_code or "").strip().upper()
    if not flight_code or len(flight_code) > 10:
        return False, "Mã chuyến bay không hợp lệ (tối đa 10 ký tự)!"

    if Flight.query.filter_by(flight_code=flight_code).first():
        return False, f"Mã chuyến bay '{flight_code}' đã tồn tại trong hệ thống!"

    airline = Airline.query.get(airline_id)
    route = FlightRoute.query.get(flight_route_id)
    if not airline or not route or route.airline_id != airline.id:
        return False, "Hãng hàng không hoặc tuyến bay không hợp lệ!"

    try:
        base_price = Decimal(str(base_price_raw))
        if base_price <= 0:
            return False, "Giá vé cơ bản phải lớn hơn 0!"
    except (InvalidOperation, TypeError, ValueError):
        return False, "Giá vé cơ bản không đúng định dạng số!"

    if not segments_input:
        return False, "Chuyến bay phải có ít nhất 1 chặng bay!"

    reg = Regulation.query.first()
    max_inter = reg.max_intermediate_airports if reg else 2
    min_flight_time = reg.min_flight_time if reg else 30
    min_stop_time = reg.min_stop_time if reg else 30
    max_stop_time = reg.max_stop_time if reg else 240

    # 1. Kiểm tra số lượng sân bay trung gian tối đa
    if len(segments_input) - 1 > max_inter:
        return False, f"Số sân bay trung gian vượt quá quy định (tối đa {max_inter} sân bay trung gian)!"

    # 2. Kiểm tra sân bay đi/đến đầu cuối khớp với Tuyến bay
    dep_afr = next((x for x in route.airport_relation if x.role == AirportRole.DEPARTURE), None)
    arr_afr = next((x for x in route.airport_relation if x.role == AirportRole.ARRIVAL), None)
    if dep_afr and segments_input[0]["dep_airport_id"] != dep_afr.airport_id:
        return False, "Sân bay xuất phát của chặng 1 không khớp với sân bay đi của tuyến bay!"
    if arr_afr and segments_input[-1]["arr_airport_id"] != arr_afr.airport_id:
        return False, "Sân bay hạ cánh của chặng cuối không khớp với sân bay đến của tuyến bay!"

    parsed_segments = []
    visited_airports = set()

    for idx, seg in enumerate(segments_input, start=1):
        dep_id = seg.get("dep_airport_id")
        arr_id = seg.get("arr_airport_id")
        plane_id = seg.get("airplane_id")

        if not dep_id or not arr_id or not plane_id:
            return False, f"Chặng {idx}: Vui lòng chọn đầy đủ sân bay đi, sân bay đến và máy bay!"
        if dep_id == arr_id:
            return False, f"Chặng {idx}: Sân bay đi và sân bay đến không được trùng nhau!"

        airplane = Airplane.query.get(plane_id)
        if not airplane or airplane.airline_id != airline.id:
            return False, f"Chặng {idx}: Máy bay được chọn không thuộc hãng {airline.name}!"

        try:
            dep_dt = datetime.strptime(seg["departure_time"], "%Y-%m-%dT%H:%M")
            arr_dt = datetime.strptime(seg["arrival_time"], "%Y-%m-%dT%H:%M")
        except (KeyError, ValueError):
            return False, f"Chặng {idx}: Thời gian khởi hành hoặc hạ cánh không hợp lệ!"

        if arr_dt <= dep_dt:
            return False, f"Chặng {idx}: Giờ hạ cánh phải sau giờ khởi hành!"

        flight_minutes = (arr_dt - dep_dt).total_seconds() / 60
        if flight_minutes < min_flight_time:
            return False, f"Chặng {idx}: Thời gian bay ({int(flight_minutes)} phút) nhỏ hơn quy định tối thiểu ({min_flight_time} phút)!"

        if idx == 1:
            visited_airports.add(dep_id)
        else:
            prev_seg = parsed_segments[-1]
            if dep_id != prev_seg["arr_airport_id"]:
                return False, f"Chặng {idx}: Sân bay đi phải trùng với sân bay đến của chặng {idx - 1}!"

            stop_minutes = (dep_dt - prev_seg["arrival_time"]).total_seconds() / 60
            if stop_minutes < min_stop_time or stop_minutes > max_stop_time:
                return False, (
                    f"Thời gian dừng tại sân bay trung gian trước chặng {idx} ({int(stop_minutes)} phút) "
                    f"phải nằm trong khoảng {min_stop_time} - {max_stop_time} phút!"
                )

        if arr_id in visited_airports:
            return False, f"Chặng {idx}: Sân bay trung gian/đến bị lặp lại trong cùng một chuyến bay!"
        visited_airports.add(arr_id)

        parsed_segments.append({
            "sequence": idx,
            "dep_airport_id": dep_id,
            "arr_airport_id": arr_id,
            "airplane_id": plane_id,
            "departure_time": dep_dt,
            "arrival_time": arr_dt
        })

    # 3. Lưu toàn bộ xuống CSDL trong 1 transaction
    try:
        new_flight = Flight(
            flight_code=flight_code,
            base_price=base_price,
            flight_route_id=route.id,
            airline_id=airline.id
        )
        db.session.add(new_flight)
        db.session.flush()

        for s in parsed_segments:
            new_seg = FlightSegment(
                departure_time=s["departure_time"],
                arrival_time=s["arrival_time"],
                sequence=s["sequence"],
                flight_id=new_flight.id,
                airplane_id=s["airplane_id"]
            )
            db.session.add(new_seg)
            db.session.flush()

            db.session.add_all([
                AirportFlightSegment(
                    role=AirportRole.DEPARTURE,
                    airport_id=s["dep_airport_id"],
                    flight_segment_id=new_seg.id
                ),
                AirportFlightSegment(
                    role=AirportRole.ARRIVAL,
                    airport_id=s["arr_airport_id"],
                    flight_segment_id=new_seg.id
                )
            ])

        db.session.commit()
        return True, f"Lập lịch chuyến bay {flight_code} ({len(parsed_segments)} chặng) thành công!"
    except Exception as e:
        db.session.rollback()
        return False, f"Lỗi lưu cơ sở dữ liệu: {str(e)}"