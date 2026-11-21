import datetime
from decimal import Decimal

# from xmlrpc.client import DateTime
from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Enum, ForeignKey, CheckConstraint, DateTime, UniqueConstraint
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship
from eapp import db,app
from enum import Enum as UserEnum
from enum import Enum as AirEnum
from enum import Enum as ClassEnum


class BaseModel(db.Model):
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)


# PHẦN USER
class UserRole(UserEnum):
    USER = 1
    STAFF = 2
    ADMIN = 3


class User(BaseModel, UserMixin):
    name = Column(String(50), nullable=False)
    avatar = Column(String(100), default='/static/user_account.png')
    username = Column(String(50), nullable=False, unique=True)
    password = Column(String(100), nullable=False)
    user_role = Column(Enum(UserRole), default=UserRole.USER)

    def __str__(self):
        return self.name


# PHẦN CHUYẾN BAY
class AirportRole(AirEnum):
    DEPARTURE = 1
    ARRIVAL = 2


class Airport(BaseModel):
    name = Column(String(100), nullable=False)
    address = Column(String(500), nullable=False)


class Airline(BaseModel):
    name = Column(String(100), unique=True, nullable=False)
    airplanes_relation = relationship('Airplane', backref='airline', lazy=True)
    flight_relation = relationship('Flight', backref='airline', lazy=True)


class Airplane(BaseModel):
    number_seat = Column(Integer, nullable=False)
    airline_id = Column(Integer, ForeignKey(Airline.id), nullable=False) # Bổ sung dòng này
    segments_relation = relationship('FlightSegment', backref='airplane', lazy=True)


class FlightRoute(BaseModel):
    name = Column(String(100), nullable=False)
    airline_id = Column(Integer, ForeignKey(Airline.id), nullable=False)
    flights_relation = relationship('Flight', backref='flight_route', lazy=True)
    airport_relation = relationship('AirportFlightRoute', backref='flight_route', lazy=True)


class AirportFlightRoute(BaseModel):
    role = Column(Enum(AirportRole), default=AirportRole.DEPARTURE, nullable=False)
    airport_id = Column(Integer, ForeignKey(Airport.id), nullable=False)
    flight_route_id = Column(Integer, ForeignKey(FlightRoute.id), nullable=False)

    # Trong AirportFlightRoute
    __table_args__ = (
        db.UniqueConstraint('flight_route_id', 'role', name='uq_route_airport_role'),
    )


class Flight(BaseModel):
    flight_code = Column(String(10), unique=True, nullable=False)
    base_price = db.Column(db.Numeric(12, 0), nullable=False)
    flight_route_id = Column(Integer, ForeignKey(FlightRoute.id), nullable=False)
    airline_id = Column(Integer, ForeignKey(Airline.id), nullable=False)
    segments_relation = relationship('FlightSegment', backref='flight', lazy=True)


class FlightSegment(BaseModel):
    departure_time = Column(DateTime, nullable=False)
    arrival_time = Column(DateTime, nullable=False)
    sequence = Column(Integer, nullable=False)

    flight_id = Column(Integer, ForeignKey(Flight.id), nullable=False)
    airplane_id = Column(Integer, ForeignKey(Airplane.id), nullable=False)

    airport_relation = relationship('AirportFlightSegment', backref='flight_segment', lazy=True)
    #boarding_relation = relationship('BoardingPass', backref='flight_segment')


    __table_args__ = (
        CheckConstraint('departure_time < arrival_time', name='check_segment_time'),
        CheckConstraint('sequence > 0', name='check_sequence_positive'),
        UniqueConstraint('flight_id', 'sequence', name='uix_flight_sequence')

    )


class AirportFlightSegment(BaseModel):
    role = Column(Enum(AirportRole), default=AirportRole.DEPARTURE, nullable=False)
    airport_id = Column(Integer, ForeignKey(Airport.id), nullable=False)
    flight_segment_id = Column(Integer, ForeignKey(FlightSegment.id), nullable=False)
    # Trong AirportFlightSegment
    __table_args__ = (
        db.UniqueConstraint('flight_segment_id', 'role', name='uq_segment_airport_role'),
    )

# ---------------------PHẦN VÉ
class SeatClass(ClassEnum):
    ECONOMY = 1
    BUSINESS = 2


class Seat(BaseModel):
    """Danh mục ghế dùng chung cho cả chuyến bay (không gắn Airplane)."""
    __tablename__ = "seat"
    seat_number = db.Column(db.String(10), nullable=False, unique=True)  # vd: A01, B12
    seat_class = db.Column(db.Enum(SeatClass), nullable=False)
    tickets = db.relationship("Ticket", back_populates="seat")


class Ticket(BaseModel):
    """Một vé = một hành khách = một ghế cho cả chuyến bay."""
    __tablename__ = "ticket"
    price = db.Column(db.Numeric(12, 0), nullable=False)  # giá chốt lúc đặt
    booking_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    flight_id = db.Column(db.Integer, db.ForeignKey("flight.id"), nullable=False)
    seat_id = db.Column(db.Integer, db.ForeignKey("seat.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    flight = db.relationship("Flight", backref="tickets")
    seat = db.relationship("Seat", back_populates="tickets")
    user = db.relationship("User", backref="tickets")
    boarding_passes = db.relationship("BoardingPass", back_populates="ticket", cascade="all, delete-orphan")

    __table_args__ = (
        # Một ghế chỉ bán một lần trong mỗi chuyến
        db.UniqueConstraint("flight_id", "seat_id", name="uq_ticket_flight_seat"),
    )


class BoardingPass(BaseModel):
    """Mỗi vé có một BoardingPass cho từng chặng của chuyến bay."""
    __tablename__ = "boarding_pass"
    ticket_id = db.Column(db.Integer, db.ForeignKey("ticket.id"), nullable=False)
    flight_segment_id = db.Column(db.Integer, db.ForeignKey("flight_segment.id"), nullable=False)
    ticket = db.relationship("Ticket", back_populates="boarding_passes")
    flight_segment = db.relationship("FlightSegment", backref="boarding_passes")

    __table_args__ = (
        db.UniqueConstraint("ticket_id", "flight_segment_id", name="uq_bp_ticket_segment"),
    )


class Regulation(BaseModel):
    """Quy định toàn hệ thống. Thường chỉ có 1 dòng."""
    __tablename__ = "regulation"
    # Quy định về sân bay / thời gian bay
    max_airports = db.Column(db.Integer, nullable=False)                  # số sân bay
    min_flight_time = db.Column(db.Integer, nullable=False)               # phút
    max_intermediate_airports = db.Column(db.Integer, nullable=False)     # sân bay trung gian tối đa
    min_stop_time = db.Column(db.Integer, nullable=False)                 # phút
    max_stop_time = db.Column(db.Integer, nullable=False)                 # phút

    # Quy định về bán vé / đặt vé (số giờ trước giờ khởi hành)
    ticket_sale_deadline = db.Column(db.Integer, nullable=False)          # thời gian bán vé
    booking_deadline = db.Column(db.Integer, nullable=False)              # thời gian đặt vé

    # Hệ số giá theo hạng ghế: price = Flight.base_price * hệ số
    economy_multiplier = db.Column(db.Numeric(4, 2), nullable=False, default=Decimal("1.00"))
    business_multiplier = db.Column(db.Numeric(4, 2), nullable=False, default=Decimal("1.50"))

    def get_multiplier(self, seat_class: SeatClass) -> Decimal:
        if seat_class == SeatClass.BUSINESS:
            return self.business_multiplier
        return self.economy_multiplier



#==============LUAT===================
class Policy(BaseModel):
    number_airport = Column(Integer, nullable=False)
    minimun_flight_time = Column(Integer, nullable=False)
    max_inter_airport = Column(Integer, nullable=False)
    minimum_stop_time = Column(Integer, nullable=False)
    maximum_stop_time = Column(Integer, nullable=False)
    number_ticket_class = Column(Integer, nullable=False)
    ticket_price = Column(Integer, nullable=False)
    ticket_sell_time = Column(Integer, nullable=False)
    ticket_booking_time = Column(Integer, nullable=False)



def seed_data():
    with app.app_context():
        # Bỏ comment dòng dưới đây nếu bạn muốn xóa sạch bảng cũ và tạo lại cấu trúc mới từ đầu:
        db.drop_all()
        db.create_all()

        # Kiểm tra nếu đã có dữ liệu thì dừng để tránh tạo trùng lặp
        if Airport.query.first():
            print("Dữ liệu mẫu đã tồn tại trong database!")
            return

        try:
            # 1. Tạo Sân bay (Airport)
            sgn = Airport(name="Tân Sơn Nhất (SGN)", address="Trường Sơn, Tân Bình, TP.HCM")
            dad = Airport(name="Đà Nẵng (DAD)", address="Duy Tân, Hải Châu, Đà Nẵng")
            han = Airport(name="Nội Bài (HAN)", address="Phú Minh, Sóc Sơn, Hà Nội")
            cxr = Airport(name="Cam Ranh (CXR)", address="Nguyễn Tất Thành, Cam Ranh, Khánh Hòa")
            db.session.add_all([sgn, dad, han, cxr])

            # 2. Tạo Hãng hàng không (Airline)
            vna = Airline(name="Vietnam Airlines")
            vja = Airline(name="Vietjet Air")
            db.session.add_all([vna, vja])
            db.session.flush()  # Đẩy tạm để lấy ID của Airport và Airline

            # 3. Tạo Máy bay (Airplane) - Đã bỏ airline_name, dùng airline_id
            plane_vna_1 = Airplane(number_seat=180, airline_id=vna.id)
            plane_vna_2 = Airplane(number_seat=250, airline_id=vna.id)
            plane_vja_1 = Airplane(number_seat=220, airline_id=vja.id)
            db.session.add_all([plane_vna_1, plane_vna_2, plane_vja_1])

            # 4. Tạo Tuyến bay (FlightRoute) - Đã bổ sung đầy đủ airline_id
            route_vna_sgn_han = FlightRoute(name="TP.HCM - Hà Nội (VNA)", airline_id=vna.id)
            route_vja_sgn_dad = FlightRoute(name="TP.HCM - Đà Nẵng (VJA)", airline_id=vja.id)
            route_vna_han_cxr = FlightRoute(name="Hà Nội - Cam Ranh (VNA)", airline_id=vna.id)
            db.session.add_all([route_vna_sgn_han, route_vja_sgn_dad, route_vna_han_cxr])
            db.session.flush()

            # 5. Gán Sân bay xuất phát & Sân bay đích cho từng Tuyến bay (AirportFlightRoute)
            route_airports = [
                # Tuyến TP.HCM -> Hà Nội
                AirportFlightRoute(role=AirportRole.DEPARTURE, airport_id=sgn.id, flight_route_id=route_vna_sgn_han.id),
                AirportFlightRoute(role=AirportRole.ARRIVAL, airport_id=han.id, flight_route_id=route_vna_sgn_han.id),
                # Tuyến TP.HCM -> Đà Nẵng
                AirportFlightRoute(role=AirportRole.DEPARTURE, airport_id=sgn.id, flight_route_id=route_vja_sgn_dad.id),
                AirportFlightRoute(role=AirportRole.ARRIVAL, airport_id=dad.id, flight_route_id=route_vja_sgn_dad.id),
                # Tuyến Hà Nội -> Cam Ranh
                AirportFlightRoute(role=AirportRole.DEPARTURE, airport_id=han.id, flight_route_id=route_vna_han_cxr.id),
                AirportFlightRoute(role=AirportRole.ARRIVAL, airport_id=cxr.id, flight_route_id=route_vna_han_cxr.id),
            ]
            db.session.add_all(route_airports)

            # 6. Tạo Chuyến bay (Flight)
            flight_1 = Flight(flight_code="VN210", flight_route_id=route_vna_sgn_han.id, airline_id=vna.id)
            flight_2 = Flight(flight_code="VJ120", flight_route_id=route_vja_sgn_dad.id, airline_id=vja.id)
            flight_3 = Flight(flight_code="VN1555", flight_route_id=route_vna_han_cxr.id, airline_id=vna.id)
            db.session.add_all([flight_1, flight_2, flight_3])
            db.session.flush()

            # 7. Tạo Chặng bay (FlightSegment)
            # Chuyến VN210: Bay nối chuyến 2 chặng (SGN -> DAD -> HAN)
            seg_1 = FlightSegment(
                departure_time=datetime(2026, 11, 25, 8, 0),
                arrival_time=datetime(2026, 11, 25, 9, 20),
                sequence=1,
                flight_id=flight_1.id,
                airplane_id=plane_vna_1.id
            )
            seg_2 = FlightSegment(
                departure_time=datetime(2026, 11, 25, 10, 30),
                arrival_time=datetime(2026, 11, 25, 12, 0),
                sequence=2,
                flight_id=flight_1.id,
                airplane_id=plane_vna_2.id
            )
            # Chuyến VJ120: Bay thẳng 1 chặng (SGN -> DAD)
            seg_3 = FlightSegment(
                departure_time=datetime(2026, 11, 25, 14, 0),
                arrival_time=datetime(2026, 11, 25, 15, 20),
                sequence=1,
                flight_id=flight_2.id,
                airplane_id=plane_vja_1.id
            )
            # Chuyến VN1555: Bay thẳng 1 chặng (HAN -> CXR)
            seg_4 = FlightSegment(
                departure_time=datetime(2026, 11, 26, 9, 15),
                arrival_time=datetime(2026, 11, 26, 11, 5),
                sequence=1,
                flight_id=flight_3.id,
                airplane_id=plane_vna_1.id
            )
            db.session.add_all([seg_1, seg_2, seg_3, seg_4])
            db.session.flush()

            # 8. Gán Sân bay đi/đến cho từng Chặng bay (AirportFlightSegment)
            segment_airports = [
                # Chặng 1 của VN210: SGN -> DAD
                AirportFlightSegment(role=AirportRole.DEPARTURE, airport_id=sgn.id, flight_segment_id=seg_1.id),
                AirportFlightSegment(role=AirportRole.ARRIVAL, airport_id=dad.id, flight_segment_id=seg_1.id),
                # Chặng 2 của VN210: DAD -> HAN
                AirportFlightSegment(role=AirportRole.DEPARTURE, airport_id=dad.id, flight_segment_id=seg_2.id),
                AirportFlightSegment(role=AirportRole.ARRIVAL, airport_id=han.id, flight_segment_id=seg_2.id),
                # Chặng 1 của VJ120: SGN -> DAD
                AirportFlightSegment(role=AirportRole.DEPARTURE, airport_id=sgn.id, flight_segment_id=seg_3.id),
                AirportFlightSegment(role=AirportRole.ARRIVAL, airport_id=dad.id, flight_segment_id=seg_3.id),
                # Chặng 1 của VN1555: HAN -> CXR
                AirportFlightSegment(role=AirportRole.DEPARTURE, airport_id=han.id, flight_segment_id=seg_4.id),
                AirportFlightSegment(role=AirportRole.ARRIVAL, airport_id=cxr.id, flight_segment_id=seg_4.id),
            ]
            db.session.add_all(segment_airports)

            db.session.commit()
            print("Tạo dữ liệu mẫu thành công!")

            # 9. Chạy thử truy vấn kiểm tra liên kết giữa các bảng
            print("\n--- KIỂM TRA DỮ LIỆU VỪA TẠO ---")
            for f in Flight.query.all():
                print(f"Chuyến bay: {f.flight_code} | Hãng: {f.airline.name} | Tuyến: {f.flight_route.name}")
                for seg in f.segments_relation:
                    san_bay_di = next(a.airport_id for a in seg.airport_relation if a.role == AirportRole.DEPARTURE)
                    san_bay_den = next(a.airport_id for a in seg.airport_relation if a.role == AirportRole.ARRIVAL)
                    ten_sb_di = Airport.query.get(san_bay_di).name
                    ten_sb_den = Airport.query.get(san_bay_den).name
                    print(f"  + Chặng {seg.sequence}: {ten_sb_di} -> {ten_sb_den} | Máy bay ID {seg.airplane_id} ({seg.airplane.number_seat} ghế)")

        except Exception as e:
            db.session.rollback()
            print("Lỗi khi tạo dữ liệu mẫu:", e)


def seed_flight_data():
    with app.app_context():
        # Đảm bảo toàn bộ bảng đã được tạo trong database
        db.create_all()

        # Tránh chèn trùng lặp nếu dữ liệu hãng bay đã tồn tại
        if Airline.query.first():
            print("Dữ liệu chuyến bay đã tồn tại trong CSDL.")
            return

        try:
            # 1. Quy định hệ thống (dùng tính giá khi chọn ghế)
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

            # 2. Sân bay
            sgn = Airport(name="Tân Sơn Nhất (SGN)", address="TP. Hồ Chí Minh")
            han = Airport(name="Nội Bài (HAN)", address="Hà Nội")
            dad = Airport(name="Đà Nẵng (DAD)", address="Đà Nẵng")
            db.session.add_all([sgn, han, dad])
            db.session.flush()

            # 3. Hãng hàng không
            vna = Airline(name="Vietnam Airlines")
            vj = Airline(name="Vietjet Air")
            db.session.add_all([vna, vj])
            db.session.flush()

            # 4. Máy bay
            plane_vna_1 = Airplane(number_seat=200, airline_id=vna.id)
            plane_vna_2 = Airplane(number_seat=200, airline_id=vna.id)
            plane_vj_1 = Airplane(number_seat=180, airline_id=vj.id)
            db.session.add_all([plane_vna_1, plane_vna_2, plane_vj_1])
            db.session.flush()

            # 5. Tuyến bay (FlightRoute) & Sân bay đầu/cuối của tuyến (AirportFlightRoute)
            route_vna_sgn_han = FlightRoute(name="Sài Gòn - Hà Nội (VNA)", airline_id=vna.id)
            route_vj_sgn_han = FlightRoute(name="Sài Gòn - Hà Nội (VJ)", airline_id=vj.id)
            route_vna_sgn_dad = FlightRoute(name="Sài Gòn - Đà Nẵng (VNA)", airline_id=vna.id)
            db.session.add_all([route_vna_sgn_han, route_vj_sgn_han, route_vna_sgn_dad])
            db.session.flush()

            db.session.add_all([
                # Tuyến SGN - HAN (VNA)
                AirportFlightRoute(role=AirportRole.DEPARTURE, airport_id=sgn.id, flight_route_id=route_vna_sgn_han.id),
                AirportFlightRoute(role=AirportRole.ARRIVAL, airport_id=han.id, flight_route_id=route_vna_sgn_han.id),
                # Tuyến SGN - HAN (VJ)
                AirportFlightRoute(role=AirportRole.DEPARTURE, airport_id=sgn.id, flight_route_id=route_vj_sgn_han.id),
                AirportFlightRoute(role=AirportRole.ARRIVAL, airport_id=han.id, flight_route_id=route_vj_sgn_han.id),
                # Tuyến SGN - DAD (VNA)
                AirportFlightRoute(role=AirportRole.DEPARTURE, airport_id=sgn.id, flight_route_id=route_vna_sgn_dad.id),
                AirportFlightRoute(role=AirportRole.ARRIVAL, airport_id=dad.id, flight_route_id=route_vna_sgn_dad.id),
            ])

            # 6. Chuyến bay (Flight)
            # Chuyến 1: VN210 (Nối chuyến 2 chặng: SGN -> DAD -> HAN)
            flight_vn210 = Flight(
                flight_code="VN210",
                base_price=Decimal("2200000"),
                flight_route_id=route_vna_sgn_han.id,
                airline_id=vna.id
            )
            # Chuyến 2: VJ120 (Bay thẳng 1 chặng: SGN -> HAN)
            flight_vj120 = Flight(
                flight_code="VJ120",
                base_price=Decimal("1500000"),
                flight_route_id=route_vj_sgn_han.id,
                airline_id=vj.id
            )
            # Chuyến 3: VN115 (Bay thẳng 1 chặng: SGN -> DAD)
            flight_vn115 = Flight(
                flight_code="VN115",
                base_price=Decimal("1200000"),
                flight_route_id=route_vna_sgn_dad.id,
                airline_id=vna.id
            )
            db.session.add_all([flight_vn210, flight_vj120, flight_vn115])
            db.session.flush()

            # 7. Chặng bay (FlightSegment)
            # 2 chặng của VN210
            seg_vn210_1 = FlightSegment(
                departure_time=datetime(2026, 12, 15, 7, 30),
                arrival_time=datetime(2026, 12, 15, 8, 50),
                sequence=1,
                flight_id=flight_vn210.id,
                airplane_id=plane_vna_1.id
            )
            seg_vn210_2 = FlightSegment(
                departure_time=datetime(2026, 12, 15, 10, 0),
                arrival_time=datetime(2026, 12, 15, 11, 20),
                sequence=2,
                flight_id=flight_vn210.id,
                airplane_id=plane_vna_2.id
            )
            # 1 chặng của VJ120
            seg_vj120_1 = FlightSegment(
                departure_time=datetime(2026, 12, 15, 9, 0),
                arrival_time=datetime(2026, 12, 15, 11, 10),
                sequence=1,
                flight_id=flight_vj120.id,
                airplane_id=plane_vj_1.id
            )
            # 1 chặng của VN115
            seg_vn115_1 = FlightSegment(
                departure_time=datetime(2026, 12, 15, 14, 15),
                arrival_time=datetime(2026, 12, 15, 15, 35),
                sequence=1,
                flight_id=flight_vn115.id,
                airplane_id=plane_vna_1.id
            )
            db.session.add_all([seg_vn210_1, seg_vn210_2, seg_vj120_1, seg_vn115_1])
            db.session.flush()

            # 8. Sân bay đi/đến từng chặng (AirportFlightSegment)
            db.session.add_all([
                # VN210 - Chặng 1: SGN -> DAD
                AirportFlightSegment(role=AirportRole.DEPARTURE, airport_id=sgn.id, flight_segment_id=seg_vn210_1.id),
                AirportFlightSegment(role=AirportRole.ARRIVAL, airport_id=dad.id, flight_segment_id=seg_vn210_1.id),
                # VN210 - Chặng 2: DAD -> HAN
                AirportFlightSegment(role=AirportRole.DEPARTURE, airport_id=dad.id, flight_segment_id=seg_vn210_2.id),
                AirportFlightSegment(role=AirportRole.ARRIVAL, airport_id=han.id, flight_segment_id=seg_vn210_2.id),
                # VJ120 - Chặng 1: SGN -> HAN
                AirportFlightSegment(role=AirportRole.DEPARTURE, airport_id=sgn.id, flight_segment_id=seg_vj120_1.id),
                AirportFlightSegment(role=AirportRole.ARRIVAL, airport_id=han.id, flight_segment_id=seg_vj120_1.id),
                # VN115 - Chặng 1: SGN -> DAD
                AirportFlightSegment(role=AirportRole.DEPARTURE, airport_id=sgn.id, flight_segment_id=seg_vn115_1.id),
                AirportFlightSegment(role=AirportRole.ARRIVAL, airport_id=dad.id, flight_segment_id=seg_vn115_1.id),
            ])

            # 9. Danh mục ghế dùng chung (10 ghế Thương gia A01-A10, 20 ghế Phổ thông B01-B20)
            seats = []
            for i in range(1, 11):
                seats.append(Seat(seat_number=f"A{i:02d}", seat_class=SeatClass.BUSINESS))
            for i in range(1, 21):
                seats.append(Seat(seat_number=f"B{i:02d}", seat_class=SeatClass.ECONOMY))
            db.session.add_all(seats)

            db.session.commit()
            print("Tạo dữ liệu mẫu phần chuyến bay thành công!")

        except Exception as e:
            db.session.rollback()
            print(f"Lỗi khởi tạo dữ liệu: {e}")

if __name__ == '__main__':
   with app.app_context():
       seed_flight_data()






