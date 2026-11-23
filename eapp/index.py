from functools import wraps
from flask import render_template, request, redirect, url_for, flash, abort
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask_login import login_user, logout_user, login_required, current_user
from cloudinary.exceptions import Error as CloudinaryError
from eapp import app, dao, login, db, admin
from eapp.models import Flight, FlightSegment, Ticket, Regulation, User, UserRole, Seat, SeatClass, BoardingPass


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

#=======================================================================================================
@app.route("/flightpage")
def flight_page_view():
    loai_ve = request.args.get("loai_ve", "mot_chieu")
    noi_di = request.args.get("noi_di", type=int)
    noi_den = request.args.get("noi_den", type=int)
    day_go = request.args.get("dayGo")
    day_back = request.args.get("dayBack")

    outbound_flights = []
    return_flights = []

    if noi_di and noi_den and day_go:
        # 1. Luôn tìm chiều đi: noi_di -> noi_den vào dayGo
        print("PARAMS NHẬN ĐƯỢC:", loai_ve, noi_di, noi_den, day_go, day_back)
        outbound_flights = dao.query_flights_by_route(noi_di, noi_den, day_go)
        print("KẾT QUẢ TRUY VẤN:", outbound_flights)

        # 2. Nếu là khứ hồi: đảo noi_den -> noi_di vào dayBack
        if loai_ve == "khu_hoi" and day_back:
            return_flights = dao.query_flights_by_route(noi_den, noi_di, day_back)

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

    # Lấy các chặng bay theo đúng thứ tự sequence (1, 2, ...)
    segments = (
        FlightSegment.query
        .filter_by(flight_id=flight.id)
        .order_by(FlightSegment.sequence.asc())
        .all()
    )

    # Lấy danh sách seat_id đã có Ticket trên chuyến bay này
    booked_seat_ids = {
        t.seat_id for t in Ticket.query.filter_by(flight_id=flight.id).all()
    }

    return {
        "flight": flight,
        "segments": segments,
        "departure_time": segments[0].departure_time if segments else None,
        "arrival_time": segments[-1].arrival_time if segments else None,
        "booked_seat_ids": booked_seat_ids
    }


@app.route("/booking", methods=["GET", "POST"])
def booking_view():
    reg = Regulation.query.first()
    eco_mult = float(reg.economy_multiplier) if reg else 1.0
    bus_mult = float(reg.business_multiplier) if reg else 1.5

    # --- XỬ LÝ LƯU VÉ KHI KHÁCH BẤM XÁC NHẬN ĐẶT ---
    if request.method == "POST":
        outbound_id = request.form.get("outbound_id", type=int)
        outbound_seat_id = request.form.get("outbound_seat_id", type=int)
        return_id = request.form.get("return_id", type=int)
        return_seat_id = request.form.get("return_seat_id", type=int)

        if not outbound_id or not outbound_seat_id:
            flash("Vui lòng chọn ghế cho chuyến đi!", "danger")
            return redirect(request.referrer or url_for("flight_page_view"))

        if return_id and not return_seat_id:
            flash("Vui lòng chọn ghế cho chuyến về!", "danger")
            return redirect(request.referrer or url_for("flight_page_view"))

        # Lấy user_id hiện tại (Nếu chưa làm chức năng đăng nhập, tự lấy/tạo 1 user test để tránh lỗi khóa ngoại)
        user = User.query.first()
        if not user:
            user = User(
                name="Khách Test",
                username="guest_test",
                phone_numbers="090000000000000",  # Phải <= 10 ký tự theo khai báo String(15)
                password="123",
                user_role=UserRole.USER
                # Cột avatar sẽ tự động nhận default='/static/user_account.png'
            )
            db.session.add(user)
            db.session.flush()

        # Gom các chặng cần xuất vé (1 phần tử nếu một chiều, 2 phần tử nếu khứ hồi)
        legs = [(outbound_id, outbound_seat_id)]
        if return_id and return_seat_id:
            legs.append((return_id, return_seat_id))

        try:
            created_tickets = []
            for f_id, s_id in legs:
                flight = Flight.query.get_or_404(f_id)
                seat = Seat.query.get_or_404(s_id)

                # Tính giá vé chính xác ở Backend
                multiplier = (
                    reg.business_multiplier
                    if seat.seat_class == SeatClass.BUSINESS
                    else reg.economy_multiplier
                )
                final_price = flight.base_price * multiplier

                # 1. Tạo Ticket (Ràng buộc UNIQUE(flight_id, seat_id) sẽ chặn nếu trùng ghế)
                ticket = Ticket(
                    price=final_price,
                    flight_id=flight.id,
                    seat_id=seat.id,
                    user_id=user.id
                )
                db.session.add(ticket)
                db.session.flush()  # Đẩy xuống DB để kiểm tra trùng ghế và lấy ticket.id

                # 2. Tự động tạo BoardingPass cho TẤT CẢ các chặng của chuyến bay này
                segments = (
                    FlightSegment.query
                    .filter_by(flight_id=flight.id)
                    .order_by(FlightSegment.sequence.asc())
                    .all()
                )
                for seg in segments:
                    db.session.add(BoardingPass(
                        ticket_id=ticket.id,
                        flight_segment_id=seg.id
                    ))

                created_tickets.append(ticket)

            # Lưu toàn bộ giao dịch
            db.session.commit()
            flash(f"Đặt vé thành công! Mã vé: {', '.join('#' + str(t.id) for t in created_tickets)}", "success")
            return redirect(url_for("flight_page_view"))

        except IntegrityError:
            db.session.rollback()
            flash("Ghế bạn chọn vừa có hành khách khác đặt trước. Vui lòng chọn ghế khác!", "danger")
            return redirect(url_for("booking_view", outbound_id=outbound_id, return_id=return_id))

        except Exception as e:
            db.session.rollback()
            flash(f"Có lỗi xảy ra khi đặt vé: {str(e)}", "danger")
            return redirect(url_for("booking_view", outbound_id=outbound_id, return_id=return_id))

    # --- HIỂN THỊ TRANG CHỌN GHẾ (GET) ---
    outbound_id = request.args.get("outbound_id", type=int)
    return_id = request.args.get("return_id", type=int)

    outbound_data = get_flight_seat_data(outbound_id)
    if not outbound_data:
        flash("Không tìm thấy thông tin chuyến bay!", "warning")
        return redirect(url_for("flight_page_view"))

    return_data = get_flight_seat_data(return_id) if return_id else None
    all_seats = Seat.query.order_by(Seat.seat_number.asc()).all()

    return render_template(
        "booking.html",
        outbound=outbound_data,
        return_flight=return_data,
        seats=all_seats,
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


if __name__ == '__main__':
    app.run(debug=True)