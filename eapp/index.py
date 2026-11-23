from flask import render_template, request, redirect, url_for, flash, Blueprint
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask_login import login_user, logout_user, login_required, current_user
from cloudinary.exceptions import Error as CloudinaryError
from sqlalchemy.orm import joinedload

from eapp import app, dao, login, db
from eapp.models import Flight, FlightSegment, Ticket, Regulation, User, UserRole, Seat, SeatClass, BoardingPass

@login.user_loader
def load_user(user_id):
    return dao.get_user_by_id(user_id)


@app.route('/')
def home_view():
    airports = dao.load_airports()
    return render_template('homepage.html', airports=airports)


@app.route('/staffpage')
def staff_view():
    return render_template('staffpage.html')

#=======================================================================================================

@app.route("/flightpage")
def flight_page_view():
    loai_ve = request.args.get("loai_ve", "mot_chieu")
    noi_di = request.args.get("noi_di", type=int)
    noi_den = request.args.get("noi_den", type=int)
    day_go = request.args.get("dayGo")
    day_back = request.args.get("dayBack")

    return_flights = []

    if noi_di and noi_den and day_go:
        outbound_flights = dao.query_flights_by_route(noi_di, noi_den, day_go)
        if loai_ve == "khu_hoi" and day_back:
            return_flights = dao.query_flights_by_route(noi_den, noi_di, day_back)
    else:
        # Không có tham số tìm kiếm -> hiển thị toàn bộ chuyến bay
        loai_ve = "mot_chieu"
        outbound_flights = dao.query_flights_by_route()

    return render_template(
        "flightpage.html",
        loai_ve=loai_ve,
        flights=outbound_flights,
        outbound_flights=outbound_flights,
        return_flights=return_flights
    )


# TRANG DAT VE VA NHAP THONG TIN
from eapp.models import Customer, CustomerPhone  # Import thêm 2 model mới
@app.route("/booking", methods=["GET", "POST"])
def booking_view():
    reg = Regulation.query.first()
    eco_mult = float(reg.economy_multiplier) if reg else 1.0
    bus_mult = float(reg.business_multiplier) if reg else 1.5

    if request.method == "POST":
        outbound_id = request.form.get("outbound_id", type=int)
        outbound_seat_id = request.form.get("outbound_seat_id", type=int)
        return_id = request.form.get("return_id", type=int)
        return_seat_id = request.form.get("return_seat_id", type=int)

        # Lấy thông tin hành khách từ form modal
        customer_name = request.form.get("customer_name", "").strip()
        raw_phones = request.form.getlist("customer_phones[]")
        valid_phones = [p.strip() for p in raw_phones if p.strip()]

        if not outbound_id or not outbound_seat_id:
            flash("Vui lòng chọn ghế cho chuyến đi!", "danger")
            return redirect(request.referrer or url_for("flight_page_view"))

        if return_id and not return_seat_id:
            flash("Vui lòng chọn ghế cho chuyến về!", "danger")
            return redirect(request.referrer or url_for("flight_page_view"))

        if not customer_name or not valid_phones:
            flash("Vui lòng nhập đầy đủ họ tên và ít nhất 1 số điện thoại hành khách!", "danger")
            return redirect(url_for("booking_view", outbound_id=outbound_id, return_id=return_id))

        #Lấy tài khoản đang đặt vé dùng tạm user test nếu chưa tích hợp current_user (Xóa chỗ này, lấy theo thông tin thật của current_user)
        if current_user.is_authenticated:
            user = current_user
            db.session.add(user)
            db.session.flush()

        legs = [(outbound_id, outbound_seat_id)]
        if return_id and return_seat_id:
            legs.append((return_id, return_seat_id))

        try:
            # 1. Lưu thông tin Customer và lấy customer.id
            customer = Customer(name=customer_name)
            db.session.add(customer)
            db.session.flush()

            # 2. Lưu các số điện thoại vào bảng customer_phone
            for phone in valid_phones:
                db.session.add(CustomerPhone(
                    phone_number=phone,
                    customer_id=customer.id
                ))

            # 3. Tạo Ticket (gắn cả user.id và customer.id) và BoardingPass
            created_tickets = []
            for f_id, s_id in legs:
                flight = Flight.query.get_or_404(f_id)
                seat = Seat.query.get_or_404(s_id)

                multiplier = (
                    reg.business_multiplier
                    if seat.seat_class == SeatClass.BUSINESS
                    else reg.economy_multiplier
                )
                final_price = flight.base_price * multiplier

                ticket = Ticket(
                    price=final_price,
                    flight_id=flight.id,
                    seat_id=seat.id,
                    user_id=user.id,
                    customer_id=customer.id
                )
                db.session.add(ticket)
                db.session.flush()

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

            db.session.commit()
            flash(
                f"Đặt vé thành công cho hành khách {customer.name}! "
                f"Mã vé: {', '.join('#' + str(t.id) for t in created_tickets)}",
                "success"
            )
            #chuyên trang xem ve thay vi quay lai trang chuyen bay
            return redirect(url_for("my_tickets"))

        except IntegrityError:
            db.session.rollback()
            flash("Ghế bạn chọn vừa có người khác đặt trước. Vui lòng chọn ghế khác!", "danger")
            return redirect(url_for("booking_view", outbound_id=outbound_id, return_id=return_id))

        except Exception as e:
            db.session.rollback()
            flash(f"Có lỗi xảy ra khi đặt vé: {str(e)}", "danger")
            return redirect(url_for("booking_view", outbound_id=outbound_id, return_id=return_id))



    # --- PHẦN GET GIỮ NGUYÊN ---
    outbound_id = request.args.get("outbound_id", type=int)
    return_id = request.args.get("return_id", type=int)

    outbound_data = dao.get_flight_seat_data(outbound_id)
    if not outbound_data:
        flash("Không tìm thấy thông tin chuyến bay!", "warning")
        return redirect(url_for("flight_page_view"))

    return_data = dao.get_flight_seat_data(return_id) if return_id else None
    all_seats = Seat.query.order_by(Seat.seat_number.asc()).all()

    return render_template(
        "booking.html",
        outbound=outbound_data,
        return_flight=return_data,
        seats=all_seats,
        eco_mult=eco_mult,
        bus_mult=bus_mult
    )


@app.route("/book", methods=["POST"])
@login_required
def book_ticket():
  flight_id = request.form.get("flight_id", type=int)
  seat_id = request.form.get("seat_id", type=int)
  customer_id = request.form.get("customer_id", type=int)
  price = request.form.get("price")

  if not all([flight_id, seat_id, customer_id, price]):
    flash("Thiếu thông tin đặt vé.", "danger")
    # Bỏ "tickets.", chỉ gọi tên hàm "my_tickets"
    return redirect(url_for("my_tickets"))

  new_ticket = Ticket(
      price=price,
      customer_id=customer_id,
      flight_id=flight_id,
      seat_id=seat_id,
      user_id=current_user.id,
  )

  try:
    db.session.add(new_ticket)
    db.session.commit()
    flash("Đặt vé thành công!", "success")
    return redirect(url_for("my_tickets"))
  except IntegrityError:
    db.session.rollback()
    flash(
        "Ghế này vừa được đặt trên chuyến bay, vui lòng chọn ghế khác.",
        "warning",
    )
    return redirect(request.referrer or url_for("my_tickets"))
  except Exception:
    db.session.rollback()
    flash("Có lỗi xảy ra khi lưu vé.", "danger")
    return redirect(request.referrer or url_for("my_tickets"))


@app.route("/my_tickets")
@login_required
def my_tickets():
  tickets = (
      Ticket.query.options(
          joinedload(Ticket.flight),
          joinedload(Ticket.seat),
          joinedload(Ticket.customer),
      )
      .filter(Ticket.user_id == current_user.id)
      .order_by(Ticket.booking_time.desc(), Ticket.id.desc())
      .all()
  )
  return render_template("my_tickets.html", tickets=tickets)

#=================================================================================================================
@app.route('/search')
def flight_search():
    return redirect(url_for('home_view'))


@app.route('/register')
def register_view():
    return render_template('register.html')


@app.route('/register', methods=['post'])
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
        except CloudinaryError:
            err_msg = 'Lỗi tải ảnh đại diện, vui lòng thử lại!'
        except IntegrityError:
            err_msg = 'Tên tài khoản hoặc số điện thoại đã tồn tại!'
        except SQLAlchemyError:
            err_msg = 'Lỗi kết nối cơ sở dữ liệu, vui lòng thử lại sau!'

    return render_template('register.html', err_msg=err_msg)


@app.route('/login')
def login_view():
    return render_template('login.html')


@app.route('/login', methods=['post'])
def login_process():
    username = request.form.get('username', '').strip()
    password = request.form.get('password')

    if not username or not password:
        err_msg = 'Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!'
    else:
        user = dao.check_login(username=username, password=password)
        if user:
            login_user(user=user)
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