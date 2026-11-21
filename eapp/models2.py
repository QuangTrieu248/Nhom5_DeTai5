from datetime import datetime
from decimal import Decimal
from sqlalchemy.exc import IntegrityError

# Import db và các model từ ứng dụng của bạn
from eapp.models import (
    db, AirportRole, Airport, Airline, Airplane,
    FlightRoute, AirportFlightRoute, Flight, FlightSegment,
    AirportFlightSegment, SeatClass, Seat, Ticket,
    BoardingPass, Regulation, User, UserRole
)


def seed_sample_data():
    try:
        # 1. Quy định hệ thống (Regulation)
        reg = Regulation(
            max_airports=10,
            min_flight_time=45,
            max_intermediate_airports=2,
            min_stop_time=30,
            max_stop_time=240,
            ticket_sale_deadline=4,
            booking_deadline=12,
            economy_multiplier=Decimal("1.00"),
            business_multiplier=Decimal("1.50")
        )
        db.session.add(reg)

        # 2. Tài khoản người dùng đặt vé (theo cấu trúc lớp User)[cite: 3]
        user1 = User(
            name="Nguyễn Văn A",
            user_name="nguyenvana",
            password="hashed_password_123",
            identity_number="079099001234",
            phone_number="0909123456",
            role=UserRole.USER
        )
        user2 = User(
            name="Trần Thị B",
            user_name="tranthib",
            password="hashed_password_456",
            identity_number="079098005678",
            phone_number="0918654321",
            role=UserRole.USER
        )
        db.session.add_all([user1, user2])

        # 3. Sân bay (3 sân bay cho tuyến nối chuyến 2 chặng)
        sgn = Airport(name="Sân bay Quốc tế Tân Sơn Nhất (SGN)", address="TP. Hồ Chí Minh")
        dad = Airport(name="Sân bay Quốc tế Đà Nẵng (DAD)", address="Đà Nẵng")
        han = Airport(name="Sân bay Quốc tế Nội Bài (HAN)", address="Hà Nội")
        db.session.add_all([sgn, dad, han])

        # 4. Hãng hàng không & 2 Máy bay (cùng cấu hình 200 ghế)
        airline = Airline(name="Vietnam Airlines")
        db.session.add(airline)
        db.session.flush()  # Lấy airline.id

        airplane_1 = Airplane(number_seat=200, airline_id=airline.id)
        airplane_2 = Airplane(number_seat=200, airline_id=airline.id)
        db.session.add_all([airplane_1, airplane_2])

        # 5. Tuyến bay (SGN -> HAN)
        route_sgn_han = FlightRoute(name="TP.HCM - Hà Nội", airline_id=airline.id)
        db.session.add(route_sgn_han)
        db.session.flush()

        db.session.add_all([
            AirportFlightRoute(role=AirportRole.DEPARTURE, airport_id=sgn.id, flight_route_id=route_sgn_han.id),
            AirportFlightRoute(role=AirportRole.ARRIVAL, airport_id=han.id, flight_route_id=route_sgn_han.id)
        ])

        # 6. Chuyến bay VN210 (Giá gốc 2,000,000 VNĐ cho cả chuyến)
        flight = Flight(
            flight_code="VN210",
            base_price=Decimal("2000000"),
            flight_route_id=route_sgn_han.id,
            airline_id=airline.id
        )
        db.session.add(flight)
        db.session.flush()

        # 7. Hai chặng bay nối chuyến (Chặng 1: SGN -> DAD, Chặng 2: DAD -> HAN)
        seg_1 = FlightSegment(
            departure_time=datetime(2026, 12, 1, 8, 0),
            arrival_time=datetime(2026, 12, 1, 9, 20),
            sequence=1,
            flight_id=flight.id,
            airplane_id=airplane_1.id
        )
        seg_2 = FlightSegment(
            departure_time=datetime(2026, 12, 1, 10, 30),
            arrival_time=datetime(2026, 12, 1, 11, 50),
            sequence=2,
            flight_id=flight.id,
            airplane_id=airplane_2.id
        )
        db.session.add_all([seg_1, seg_2])
        db.session.flush()

        # Gán sân bay đi/đến cho từng chặng
        db.session.add_all([
            AirportFlightSegment(role=AirportRole.DEPARTURE, airport_id=sgn.id, flight_segment_id=seg_1.id),
            AirportFlightSegment(role=AirportRole.ARRIVAL, airport_id=dad.id, flight_segment_id=seg_1.id),
            AirportFlightSegment(role=AirportRole.DEPARTURE, airport_id=dad.id, flight_segment_id=seg_2.id),
            AirportFlightSegment(role=AirportRole.ARRIVAL, airport_id=han.id, flight_segment_id=seg_2.id),
        ])

        # 8. Danh mục ghế dùng chung (Tạo mẫu 5 ghế Thương gia A01-A05 và 5 ghế Phổ thông B01-B05)
        seats = []
        for i in range(1, 6):
            seats.append(Seat(seat_number=f"A{i:02d}", seat_class=SeatClass.BUSINESS))
            seats.append(Seat(seat_number=f"B{i:02d}", seat_class=SeatClass.ECONOMY))
        db.session.add_all(seats)
        db.session.flush()

        # Lấy ghế A01 (Thương gia) và B01 (Phổ thông) để test đặt vé
        seat_a01 = next(s for s in seats if s.seat_number == "A01")
        seat_b01 = next(s for s in seats if s.seat_number == "B01")

        # 9. Giao dịch đặt vé 1: User 1 đặt ghế A01 trên chuyến VN210
        # Giá vé = 2,000,000 * 1.50 = 3,000,000 VNĐ
        final_price = flight.base_price * reg.get_multiplier(seat_a01.seat_class)
        ticket_1 = Ticket(
            price=final_price,
            flight_id=flight.id,
            seat_id=seat_a01.id,
            user_id=user1.id
        )
        db.session.add(ticket_1)
        db.session.flush()

        # Tự động tạo 2 BoardingPass cho 2 chặng của chuyến bay
        for seg in [seg_1, seg_2]:
            db.session.add(BoardingPass(ticket_id=ticket_1.id, flight_segment_id=seg.id))

        db.session.commit()
        print(f"Khởi tạo thành công! Vé #{ticket_1.id} - Ghế {seat_a01.seat_number} - Giá: {ticket_1.price:,.0f} VNĐ")

        # 10. Kiểm thử ràng buộc UNIQUE(flight_id, seat_id): User 2 cố tình đặt trùng ghế A01
        try:
            duplicate_ticket = Ticket(
                price=final_price,
                flight_id=flight.id,
                seat_id=seat_a01.id,
                user_id=user2.id
            )
            db.session.add(duplicate_ticket)
            db.session.flush()
            for seg in [seg_1, seg_2]:
                db.session.add(BoardingPass(ticket_id=duplicate_ticket.id, flight_segment_id=seg.id))
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            print("Test thành công: Hệ thống đã chặn đặt trùng ghế A01 và rollback giao dịch!")

    except Exception as e:
        db.session.rollback()
        print(f"Lỗi khởi tạo dữ liệu: {e}")