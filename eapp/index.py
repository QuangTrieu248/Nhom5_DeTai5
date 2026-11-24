from datetime import datetime, timedelta
from functools import wraps
from flask import render_template, request, redirect, url_for, flash, abort
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask_login import login_user, logout_user, login_required, current_user
from cloudinary.exceptions import Error as CloudinaryError
from eapp import app, dao, login, db, admin
from eapp.models import (
    Airport,
    AirportRole,
    BoardingPass,
    Customer,
    Flight,
    FlightSegment,
    Regulation,
    Seat,
    SeatClass,
    Ticket,
    User,
    UserRole,
    AirportFlightSegment,
)

def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.user_role not in [UserRole.STAFF, UserRole.ADMIN]:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function


@login.user_loader
def load_user(user_id):
    return dao.get_user_by_id(user_id)


@app.route('/')
def home_view():
    airports = dao.load_airports()
    return render_template('homepage.html', airports=airports)


@app.route('/staffpage', methods=['GET', 'POST'])
@staff_required
def staff_view():
    if request.method == 'POST':
        flight_code = request.form.get('flight_code')
        airline_id = request.form.get('airline_id', type=int)
        flight_route_id = request.form.get('flight_route_id', type=int)
        base_price = request.form.get('base_price')

        dep_ids = request.form.getlist('dep_airport_id[]', type=int)
        arr_ids = request.form.getlist('arr_airport_id[]', type=int)
        plane_ids = request.form.getlist('airplane_id[]', type=int)
        dep_times = request.form.getlist('departure_time[]')
        arr_times = request.form.getlist('arrival_time[]')

        segments_input = []
        for i in range(len(dep_ids)):
            segments_input.append({
                'dep_airport_id': dep_ids[i],
                'arr_airport_id': arr_ids[i] if i < len(arr_ids) else None,
                'airplane_id': plane_ids[i] if i < len(plane_ids) else None,
                'departure_time': dep_times[i] if i < len(dep_times) else '',
                'arrival_time': arr_times[i] if i < len(arr_times) else ''
            })

        ok, msg = dao.create_scheduled_flight(
            flight_code=flight_code,
            airline_id=airline_id,
            flight_route_id=flight_route_id,
            base_price_raw=base_price,
            segments_input=segments_input
        )
        flash(msg, 'success' if ok else 'danger')
        if ok:
            return redirect(url_for('staff_view'))

    form_data = dao.get_schedule_form_data()
    return render_template('staffpage.html', **form_data)

@app.route('/staff/sell-ticket', methods=['POST'])
@staff_required
def staff_sell_ticket_view():
    flight_id = request.form.get('flight_id', type=int)
    seat_id = request.form.get('seat_id', type=int)
    passenger_name = request.form.get('passenger_name')
    passenger_phone = request.form.get('passenger_phone')

    ok, msg = dao.sell_counter_ticket(
        flight_id=flight_id,
        seat_id=seat_id,
        passenger_name=passenger_name,
        passenger_phone=passenger_phone,
        staff_id=current_user.id
    )
    flash(msg, 'success' if ok else 'danger')
    return redirect(url_for('staff_view'))

#=======================================================================================================
@app.route("/flightpage")
def flight_page_view():
    loai_ve = request.args.get("loai_ve", "mot_chieu")
    noi_di = request.args.get("noi_di", type=int)
    noi_den = request.args.get("noi_den", type=int)
    day_go = (request.args.get("dayGo") or "").strip()
    day_back = (request.args.get("dayBack") or "").strip()

    outbound_flights = []
    return_flights = []

    if noi_di and noi_den and day_go:
        # 1. Tìm đúng tuyến và ngày đi được chọn
        outbound_flights = dao.query_flights_by_route(noi_di, noi_den, day_go)

        # 2. Nếu là khứ hồi: đảo noi_den -> noi_di vào dayBack
        if loai_ve == "khu_hoi" and day_back:
            return_flights = dao.query_flights_by_route(noi_den, noi_di, day_back)
    else:
        # Khi bấm "Xem tất cả chuyến bay" hoặc bỏ trống một vài ô tìm kiếm:
        # Gom các cặp (sân bay đi, sân bay đến, ngày đi) của các chuyến sắp bay để gọi qua dao
        now = datetime.now()
        search_keys = set()

        for f in Flight.query.all():
            segs = (
                FlightSegment.query
                .filter_by(flight_id=f.id)
                .order_by(FlightSegment.sequence.asc())
                .all()
            )
            if not segs or segs[0].departure_time <= now:
                continue

            dep_link = AirportFlightSegment.query.filter_by(
                flight_segment_id=segs[0].id, role=AirportRole.DEPARTURE
            ).first()
            arr_link = AirportFlightSegment.query.filter_by(
                flight_segment_id=segs[-1].id, role=AirportRole.ARRIVAL
            ).first()

            if not dep_link or not arr_link:
                continue

            d_id = dep_link.airport_id
            a_id = arr_link.airport_id
            d_str = segs[0].departure_time.strftime("%Y-%m-%d")

            if noi_di and d_id != noi_di:
                continue
            if noi_den and a_id != noi_den:
                continue
            if day_go and d_str != day_go:
                continue

            search_keys.add((d_id, a_id, d_str))

        for d_id, a_id, d_str in sorted(search_keys, key=lambda x: x[2]):
            outbound_flights.extend(dao.query_flights_by_route(d_id, a_id, d_str))

    return render_template(
        "flightpage.html",
        loai_ve=loai_ve,
        outbound_flights=outbound_flights,
        return_flights=return_flights
    )

def get_flight_seat_data(flight_id):
    """Lấy thông tin chuyến bay, danh sách chặng và tập ID các ghế đã bị đặt."""
    if not flight_id:
        return None
    flight = Flight.query.get(flight_id)
    if not flight:
        return None

    segments = sorted(flight.segments_relation, key=lambda s: s.sequence)
    airport_map = {a.id: a.name for a in Airport.query.all()}
    seg_list = []
    for s in segments:
        dep_s = next((x for x in s.airport_relation if x.role == AirportRole.DEPARTURE), None)
        arr_s = next((x for x in s.airport_relation if x.role == AirportRole.ARRIVAL), None)
        seg_list.append({
            "sequence": s.sequence,
            "dep_name": airport_map.get(dep_s.airport_id, "N/A") if dep_s else "N/A",
            "arr_name": airport_map.get(arr_s.airport_id, "N/A") if arr_s else "N/A",
            "departure_time": s.departure_time,
            "arrival_time": s.arrival_time
        })

    booked_seat_ids = {t.seat_id for t in Ticket.query.filter_by(flight_id=flight.id).all()}

    return {
        "flight": flight,
        "segments": seg_list,
        "booked_seat_ids": booked_seat_ids
    }



@app.route("/booking", methods=["GET", "POST"])
@login_required
def booking_view():
    reg = Regulation.query.first()
    eco_mult = float(reg.economy_multiplier) if reg else 1.0
    bus_mult = float(reg.business_multiplier) if reg else 1.5
    booking_deadline = reg.booking_deadline if reg else 12

    if request.method == "POST":
        outbound_id = request.form.get("outbound_id", type=int)
        outbound_seat_id = request.form.get("outbound_seat_id", type=int)

        is_round_trip = request.form.get("is_round_trip") == "1"
        inbound_id = request.form.get("inbound_id", type=int) if is_round_trip else None
        inbound_seat_id = request.form.get("inbound_seat_id", type=int) if is_round_trip else None

        passenger_name = (request.form.get("passenger_name") or "").strip()
        passenger_phone = (request.form.get("passenger_phone") or "").strip()

        if not outbound_id or not outbound_seat_id:
            flash("Vui lòng chọn ghế cho chuyến bay chiều đi!", "danger")
            return redirect(request.referrer or url_for("flight_page_view"))

        if is_round_trip and (not inbound_id or not inbound_seat_id):
            flash("Vui lòng chọn chuyến bay và ghế ngồi cho chiều về!", "danger")
            return redirect(url_for("booking_view", outbound_id=outbound_id))

        if not passenger_name or not passenger_phone:
            flash("Vui lòng nhập đầy đủ họ tên và số điện thoại hành khách!", "danger")
            return redirect(url_for("booking_view", outbound_id=outbound_id, inbound_id=inbound_id))

        try:
            # --- 1. KIỂM TRA CHUYẾN ĐI ---
            out_flight = Flight.query.get_or_404(outbound_id)
            out_seat = Seat.query.get_or_404(outbound_seat_id)
            out_data = get_flight_seat_data(out_flight.id)
            out_segments = (
                FlightSegment.query
                .filter_by(flight_id=out_flight.id)
                .order_by(FlightSegment.sequence.asc())
                .all()
            )
            if not out_segments or not out_data or not out_data.get("segments"):
                flash("Chuyến bay chiều đi chưa có lịch trình chặng bay!", "danger")
                return redirect(url_for("flight_page_view"))

            if out_segments[0].departure_time - datetime.now() < timedelta(hours=booking_deadline):
                flash(
                    f"Chuyến {out_flight.flight_code} đã quá hạn đặt vé trực tuyến "
                    f"(phải đặt trước ít nhất {booking_deadline} giờ)!",
                    "danger"
                )
                return redirect(url_for("flight_page_view"))

            if Ticket.query.filter_by(flight_id=out_flight.id, seat_id=out_seat.id).first():
                flash("Ghế chiều đi bạn chọn vừa có người đặt trước. Vui lòng chọn ghế khác!", "danger")
                return redirect(url_for("booking_view", outbound_id=outbound_id, inbound_id=inbound_id))

            # --- 2. KIỂM TRA CHUYẾN VỀ (NẾU KHỨ HỒI) ---
            in_flight = None
            in_seat = None
            in_segments = []
            if is_round_trip:
                in_flight = Flight.query.get_or_404(inbound_id)
                in_seat = Seat.query.get_or_404(inbound_seat_id)
                in_data = get_flight_seat_data(in_flight.id)
                in_segments = (
                    FlightSegment.query
                    .filter_by(flight_id=in_flight.id)
                    .order_by(FlightSegment.sequence.asc())
                    .all()
                )
                if not in_segments or not in_data or not in_data.get("segments"):
                    flash("Chuyến bay chiều về chưa có lịch trình chặng bay!", "danger")
                    return redirect(url_for("booking_view", outbound_id=outbound_id))

                out_origin_name = out_data["segments"][0]["dep_name"]
                out_dest_name = out_data["segments"][-1]["arr_name"]
                in_origin_name = in_data["segments"][0]["dep_name"]
                in_dest_name = in_data["segments"][-1]["arr_name"]

                if in_origin_name != out_dest_name or in_dest_name != out_origin_name:
                    flash("Chuyến bay chiều về phải là tuyến ngược lại của chiều đi!", "danger")
                    return redirect(url_for("booking_view", outbound_id=outbound_id))

                if in_segments[0].departure_time <= out_segments[-1].arrival_time:
                    flash("Giờ khởi hành chiều về phải sau giờ hạ cánh chiều đi!", "danger")
                    return redirect(url_for("booking_view", outbound_id=outbound_id))

                if in_segments[0].departure_time - datetime.now() < timedelta(hours=booking_deadline):
                    flash(
                        f"Chuyến về {in_flight.flight_code} đã quá hạn đặt vé trực tuyến "
                        f"(phải đặt trước ít nhất {booking_deadline} giờ)!",
                        "danger"
                    )
                    return redirect(url_for("booking_view", outbound_id=outbound_id))

                if Ticket.query.filter_by(flight_id=in_flight.id, seat_id=in_seat.id).first():
                    flash("Ghế chiều về bạn chọn vừa có người đặt trước. Vui lòng chọn ghế khác!", "danger")
                    return redirect(url_for("booking_view", outbound_id=outbound_id, inbound_id=inbound_id))

            # --- 3. LƯU HÀNH KHÁCH (CUSTOMER) ---
            customer = Customer.query.filter_by(name=passenger_name, phone=passenger_phone).first()
            if not customer:
                customer = Customer(name=passenger_name, phone=passenger_phone)
                db.session.add(customer)
                db.session.flush()

            # --- 4. TẠO VÉ CHIỀU ĐI + BOARDING PASSES ---
            out_mult = (
                reg.business_multiplier
                if out_seat.seat_class == SeatClass.BUSINESS
                else reg.economy_multiplier
            )
            out_price = out_flight.base_price * out_mult

            out_ticket = Ticket(
                price=out_price,
                booking_time=datetime.now(),
                flight_id=out_flight.id,
                seat_id=out_seat.id,
                user_id=current_user.id,
                customer_id=customer.id
            )
            db.session.add(out_ticket)
            db.session.flush()

            for seg in out_segments:
                db.session.add(BoardingPass(
                    ticket_id=out_ticket.id,
                    flight_segment_id=seg.id
                ))

            # --- 5. TẠO VÉ CHIỀU VỀ + BOARDING PASSES (NẾU KHỨ HỒI) ---
            if is_round_trip:
                in_mult = (
                    reg.business_multiplier
                    if in_seat.seat_class == SeatClass.BUSINESS
                    else reg.economy_multiplier
                )
                in_price = in_flight.base_price * in_mult

                in_ticket = Ticket(
                    price=in_price,
                    booking_time=datetime.now(),
                    flight_id=in_flight.id,
                    seat_id=in_seat.id,
                    user_id=current_user.id,
                    customer_id=customer.id
                )
                db.session.add(in_ticket)
                db.session.flush()

                for seg in in_segments:
                    db.session.add(BoardingPass(
                        ticket_id=in_ticket.id,
                        flight_segment_id=seg.id
                    ))

            db.session.commit()

            if is_round_trip:
                flash(
                    f"Đặt vé khứ hồi thành công cho {customer.name} ({customer.phone}): "
                    f"Vé đi #{out_ticket.id} ({out_flight.flight_code} - Ghế {out_seat.seat_number}) & "
                    f"Vé về #{in_ticket.id} ({in_flight.flight_code} - Ghế {in_seat.seat_number})!",
                    "success"
                )
            else:
                flash(
                    f"Đặt vé #{out_ticket.id} thành công cho hành khách {customer.name} ({customer.phone}) "
                    f"- Ghế {out_seat.seat_number}!",
                    "success"
                )
            return redirect(url_for("my_tickets_view"))

        except IntegrityError:
            db.session.rollback()
            flash("Ghế bạn chọn vừa có hành khách khác đặt trước. Vui lòng chọn ghế khác!", "danger")
            return redirect(url_for("booking_view", outbound_id=outbound_id, inbound_id=inbound_id))

        except Exception as e:
            db.session.rollback()
            flash(f"Có lỗi xảy ra khi đặt vé: {str(e)}", "danger")
            return redirect(url_for("booking_view", outbound_id=outbound_id, inbound_id=inbound_id))

    # --- GET: TẢI DỮ LIỆU CHIỀU ĐI & DANH SÁCH CHUYẾN VỀ TUYẾN NGƯỢC LẠI ---
    outbound_id = request.args.get("outbound_id", type=int)
    preselected_inbound_id = request.args.get("inbound_id", type=int)

    outbound_data = get_flight_seat_data(outbound_id)
    if not outbound_data or not outbound_data.get("segments"):
        flash("Không tìm thấy thông tin chuyến bay!", "warning")
        return redirect(url_for("flight_page_view"))

    out_origin_name = outbound_data["segments"][0]["dep_name"]
    out_dest_name = outbound_data["segments"][-1]["arr_name"]
    out_final_arrival = outbound_data["segments"][-1]["arrival_time"]

    all_seats = Seat.query.order_by(Seat.seat_number.asc()).all()
    all_seats_json = [
        {
            "id": s.id,
            "seat_number": s.seat_number,
            "is_business": (s.seat_class == SeatClass.BUSINESS)
        }
        for s in all_seats
    ]

    # Chỉ lấy các chuyến bay xuất phát đúng tại điểm đến cuối cùng (out_dest_name)
    # và hạ cánh đúng tại điểm đi ban đầu (out_origin_name)
    return_flights_json = []
    candidate_flights = Flight.query.filter(Flight.id != outbound_id).all()
    for f in candidate_flights:
        f_data = get_flight_seat_data(f.id)
        if not f_data or not f_data.get("segments"):
            continue

        f_origin_name = f_data["segments"][0]["dep_name"]
        f_dest_name = f_data["segments"][-1]["arr_name"]
        f_first_dep = f_data["segments"][0]["departure_time"]

        if (
            f_origin_name == out_dest_name
            and f_dest_name == out_origin_name
            and f_first_dep > out_final_arrival
            and (f_first_dep - datetime.now() >= timedelta(hours=booking_deadline))
            and len(f_data["booked_seat_ids"]) < len(all_seats)
        ):
            return_flights_json.append({
                "id": f.id,
                "flight_code": f.flight_code,
                "airline_name": f.airline.name,
                "route_name": f.flight_route.name,
                "base_price": float(f.base_price),
                "booked_seat_ids": list(f_data["booked_seat_ids"]),
                "segments": [
                    {
                        "sequence": s["sequence"],
                        "dep_name": s["dep_name"],
                        "arr_name": s["arr_name"],
                        "dep_time": s["departure_time"].strftime("%d/%m/%Y %H:%M"),
                        "arr_time": s["arrival_time"].strftime("%H:%M")
                    }
                    for s in f_data["segments"]
                ]
            })

    return render_template(
        "booking.html",
        outbound=outbound_data,
        seats=all_seats,
        all_seats_json=all_seats_json,
        return_flights_json=return_flights_json,
        preselected_inbound_id=preselected_inbound_id,
        eco_mult=eco_mult,
        bus_mult=bus_mult
    )

#==================================================================================================================
@app.route('/search')
def flight_search():
    return redirect(url_for('home_view'))


@app.route('/register')
def register_view():
    return render_template('register.html')


@app.route('/register', methods=['POST'])
def register_process():
    name = request.form.get('fullname', '').strip()
    username = request.form.get('username', '').strip()
    phone = request.form.get('phone', '').strip()
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    avatar_file = request.files.get('avatar')

    if not name or not username or not phone or not password:
        err_msg = 'Vui lòng nhập đầy đủ họ tên, tên đăng nhập, số điện thoại và mật khẩu!'
    elif not confirm_password or password != confirm_password:
        err_msg = 'Mật khẩu xác nhận không khớp!'
    elif dao.get_user_by_username(username):
        err_msg = 'Tên tài khoản đã được đặt, vui lòng chọn tên khác!'
    elif dao.get_phone_number(phone):
        err_msg = 'Số điện thoại này đã đăng ký tài khoản!'
    else:
        try:
            dao.add_user(
                name=name,
                username=username,
                password=password,
                phone=phone,
                avatar=avatar_file
            )
            return redirect(url_for('login_view'))
        except CloudinaryError as ex:
            print("LỖI CLOUDINARY:", ex)
            err_msg = 'Lỗi tải ảnh đại diện, vui lòng thử lại!'
        except IntegrityError as ex:
            db.session.rollback()
            print("LỖI TRÙNG DỮ LIỆU SQL:", ex)
            err_msg = 'Tên tài khoản hoặc số điện thoại đã tồn tại!'
        except SQLAlchemyError as ex:
            db.session.rollback()
            print("LỖI DATABASE SQL:", ex)
            err_msg = 'Lỗi kết nối cơ sở dữ liệu, vui lòng thử lại sau!'

    return render_template('register.html', err_msg=err_msg)


@app.route('/login')
def login_view():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login_process():
    username = request.form.get('username', '').strip()
    password = request.form.get('password')

    if not username or not password:
        err_msg = 'Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!'
    else:
        user = dao.check_login(username=username, password=password)
        if user:
            login_user(user=user)
            if user.user_role == UserRole.ADMIN:
                return redirect('/admin')
            elif user.user_role == UserRole.STAFF:
                return redirect(url_for('staff_view'))
            return redirect(url_for('home_view'))
        else:
            err_msg = 'Tên đăng nhập hoặc mật khẩu không chính xác!'

    return render_template('login.html', err_msg=err_msg)


@app.route('/logout')
@login_required
def logout_view():
    logout_user()
    return redirect(url_for('login_view'))

@app.route("/my-tickets")
@login_required
def my_tickets_view():
    tickets = (
        Ticket.query
        .filter_by(user_id=current_user.id)
        .order_by(Ticket.booking_time.desc(), Ticket.id.desc())
        .all()
    )

    for t in tickets:
        t.ordered_segments = (
            FlightSegment.query
            .filter_by(flight_id=t.flight_id)
            .order_by(FlightSegment.sequence.asc())
            .all()
        )

    return render_template("mytickets.html", tickets=tickets)

if __name__ == '__main__':
    app.run(debug=True)