# import datetime
# from decimal import Decimal
#
# from flask_login import UserMixin
# from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, CheckConstraint, text, UniqueConstraint, \
#     Numeric
# from sqlalchemy.orm import relationship
# from eapp import db, app
# from enum import Enum as UserRoleEnum
# from enum import Enum as AirportRoleEnum
# from enum import Enum as SeatClassEnum

import datetime
import hashlib
from decimal import Decimal

# from xmlrpc.client import DateTime
from flask_login import UserMixin
from sqlalchemy.orm import relationship
from eapp import db, app
from enum import Enum as UserEnum
from enum import Enum as AirportRoleEnum
from enum import Enum as UserRoleEnum
from enum import Enum as SeatClassEnum


from sqlalchemy import Column, Integer, String, Enum, ForeignKey, CheckConstraint, DateTime, UniqueConstraint, Numeric, text
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta


class BaseModel(db.Model):
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)


#--------------------------- PHẦN USER-------------------------------
class UserRole(UserRoleEnum):
    USER = 1
    STAFF = 2
    ADMIN = 3


UserRoleEnum = UserRole


class User(BaseModel, UserMixin):
    name = Column(String(50), nullable=False)
    avatar = Column(String(255), default='/static/user_account.png')
    username = Column(String(50), nullable=False, unique=True)
    phone = Column(String(15), nullable=False, unique=True)
    password = Column(String(100), nullable=False)
    user_role = Column(Enum(UserRole), default=UserRole.USER)

    def __str__(self):
        return self.name

class Customer(BaseModel):
    __tablename__ = "customer"

    name = Column(db.String(100), nullable=False)
    phone = Column(db.String(20), nullable=False)

    tickets = relationship("Ticket", backref="customer", lazy=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"



#------------------------------------ PHẦN CHUYẾN BAY--------------------------
class AirportRole(AirportRoleEnum):
    DEPARTURE = 1
    ARRIVAL = 2


class Airport(BaseModel):
    name = Column(String(100), nullable=False)
    address = Column(String(500), nullable=False)

    def __str__(self):
        return self.name


class Airline(BaseModel):
    name = Column(String(100), unique=True, nullable=False)
    airplanes_relation = relationship('Airplane', backref='airline', lazy=True)
    flight_relation = relationship('Flight', backref='airline', lazy=True)

    def __str__(self):
        return self.name


class Airplane(BaseModel):
    number_seat = Column(Integer, nullable=False)
    airline_id = Column(Integer, ForeignKey(Airline.id), nullable=False) # Bổ sung dòng này
    segments_relation = relationship('FlightSegment', backref='airplane', lazy=True)

    def __str__(self):
        return f"{self.airline.name} ({self.number_seat} ghế)" if self.airline else f"Máy bay #{self.id}"


class FlightRoute(BaseModel):
    name = Column(String(100), nullable=False)
    airline_id = Column(Integer, ForeignKey(Airline.id), nullable=False)
    flights_relation = relationship('Flight', backref='flight_route', lazy=True)
    airport_relation = relationship('AirportFlightRoute', backref='flight_route', lazy=True)
    airline = relationship('Airline', backref='flight_routes', lazy=True)

    def __str__(self):
        return self.name


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

    def __str__(self):
        return self.flight_code


class FlightSegment(BaseModel):
    departure_time = Column(DateTime, nullable=False)
    arrival_time = Column(DateTime, nullable=False)
    sequence = Column(Integer, nullable=False)

    flight_id = Column(Integer, ForeignKey(Flight.id), nullable=False)
    airplane_id = Column(Integer, ForeignKey(Airplane.id), nullable=False)
    airport_relation = relationship('AirportFlightSegment', backref='flight_segment', lazy=True)

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


# ---------------------PHẦN VÉ-----------
class SeatClass(SeatClassEnum):
    ECONOMY = 1
    BUSINESS = 2


class Seat(BaseModel):
    """Danh mục ghế dùng chung cho cả chuyến bay (không gắn Airplane)."""
    __tablename__ = "seat"
    seat_number = Column(String(10), nullable=False, unique=True)  # vd: A01, B12
    seat_class = Column(Enum(SeatClass), nullable=False)
    tickets = relationship("Ticket", back_populates="seat")


class Ticket(BaseModel):
    __tablename__ = "ticket"

    price = Column(db.Numeric(10, 2), nullable=False)
    booking_time = Column(db.DateTime, nullable=False, default=datetime.now)

    flight_id = Column(db.Integer, db.ForeignKey(Flight.id), nullable=False)
    seat_id = Column(db.Integer, db.ForeignKey(Seat.id), nullable=False)
    user_id = Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    customer_id = Column(db.Integer, db.ForeignKey(Customer.id), nullable=False)
    flight = relationship("Flight", backref="tickets")
    seat = relationship("Seat", back_populates="tickets")
    boarding_passes = relationship("BoardingPass", back_populates="ticket", cascade="all, delete-orphan")
    __table_args__ = (
        UniqueConstraint("flight_id", "seat_id", name="uq_ticket_flight_seat"),
    )


class BoardingPass(BaseModel):
    """Mỗi vé có một BoardingPass cho từng chặng của chuyến bay."""
    __tablename__ = "boarding_pass"
    ticket_id = Column(db.Integer, db.ForeignKey("ticket.id"), nullable=False)
    flight_segment_id = Column(db.Integer, db.ForeignKey("flight_segment.id"), nullable=False)

    ticket = relationship("Ticket", back_populates="boarding_passes")
    flight_segment = relationship("FlightSegment", backref="boarding_passes")

    __table_args__ = (
        db.UniqueConstraint("ticket_id", "flight_segment_id", name="uq_bp_ticket_segment"),
    )


class Regulation(BaseModel):
    """Quy định toàn hệ thống. Thường chỉ có 1 dòng."""
    __tablename__ = "regulation"
    # Quy định về sân bay / thời gian bay
    max_airports = Column(db.Integer, nullable=False)                  # số sân bay
    min_flight_time = Column(db.Integer, nullable=False)               # phút
    max_intermediate_airports = Column(db.Integer, nullable=False)     # sân bay trung gian tối đa
    min_stop_time = Column(db.Integer, nullable=False)                 # phút
    max_stop_time = Column(db.Integer, nullable=False)                 # phút

    # Quy định về bán vé / đặt vé (số giờ trước giờ khởi hành)
    ticket_sale_deadline = Column(db.Integer, nullable=False)          # thời gian bán vé
    booking_deadline = Column(db.Integer, nullable=False)              # thời gian đặt vé

    # Hệ số giá theo hạng ghế: price = Flight.base_price * hệ số
    economy_multiplier = Column(db.Numeric(4, 2), nullable=False, default=Decimal("1.00"))
    business_multiplier = Column(db.Numeric(4, 2), nullable=False, default=Decimal("1.50"))

    def get_multiplier(self, seat_class: SeatClass) -> Decimal:
        if seat_class == SeatClass.BUSINESS:
            return self.business_multiplier
        return self.economy_multiplier



def seed_flight_data():
    with app.app_context():
        # Đảm bảo toàn bộ bảng đã được tạo trong database
        db.create_all()

        # Tránh chèn trùng lặp nếu dữ liệu hãng bay đã tồn tại
        if Airline.query.first():
            print("Dữ liệu chuyến bay đã tồn tại trong CSDL.")
            return

        try:
            # 0. Tài khoản Admin mặc định
            if not User.query.filter_by(username="admin").first():
                admin_acc = User(
                    name="Quản trị viên",
                    username="admin",
                    phone="0900000000",
                    password=hashlib.md5("123456".encode("utf-8")).hexdigest(),
                    user_role=UserRole.ADMIN
                )
                db.session.add(admin_acc)

            # 1. Quy định hệ thống
            reg = Regulation(
                max_airports=10,
                min_flight_time=30,
                max_intermediate_airports=2,
                min_stop_time=20,
                max_stop_time=30,
                ticket_sale_deadline=4,
                booking_deadline=12,
                economy_multiplier=Decimal("1.00"),
                business_multiplier=Decimal("1.50")
            )
            db.session.add(reg)

            # 2. Khởi tạo 10 Sân bay
            sgn = Airport(name="Tân Sơn Nhất (SGN)", address="TP. Hồ Chí Minh")
            han = Airport(name="Nội Bài (HAN)", address="Hà Nội")
            dad = Airport(name="Đà Nẵng (DAD)", address="Đà Nẵng")
            cxr = Airport(name="Cam Ranh (CXR)", address="Khánh Hòa")
            pqc = Airport(name="Phú Quốc (PQC)", address="Kiên Giang")
            dli = Airport(name="Liên Khương (DLI)", address="Lâm Đồng")
            hph = Airport(name="Cát Bi (HPH)", address="Hải Phòng")
            vca = Airport(name="Cần Thơ (VCA)", address="Cần Thơ")
            hui = Airport(name="Phú Bài (HUI)", address="Thừa Thiên Huế")
            vii = Airport(name="Vinh (VII)", address="Nghệ An")
            db.session.add_all([sgn, han, dad, cxr, pqc, dli, hph, vca, hui, vii])
            db.session.flush()

            # 3. Khởi tạo 4 Hãng hàng không
            vna = Airline(name="Vietnam Airlines")
            vj = Airline(name="Vietjet Air")
            bav = Airline(name="Bamboo Airways")
            vua = Airline(name="Vietravel Airlines")
            db.session.add_all([vna, vj, bav, vua])
            db.session.flush()

            # 4. Máy bay
            plane_vna_1 = Airplane(number_seat=200, airline_id=vna.id)
            plane_vna_2 = Airplane(number_seat=200, airline_id=vna.id)
            plane_vj_1 = Airplane(number_seat=180, airline_id=vj.id)
            plane_vj_2 = Airplane(number_seat=180, airline_id=vj.id)
            plane_bav_1 = Airplane(number_seat=150, airline_id=bav.id)
            plane_vua_1 = Airplane(number_seat=180, airline_id=vua.id)
            db.session.add_all([plane_vna_1, plane_vna_2, plane_vj_1, plane_vj_2, plane_bav_1, plane_vua_1])
            db.session.flush()

            # Hàm hỗ trợ tạo Tuyến bay (FlightRoute) + 2 đầu sân bay (AirportFlightRoute)
            def create_route(route_name, airline_obj, dep_ap, arr_ap):
                rt = FlightRoute(name=route_name, airline_id=airline_obj.id)
                db.session.add(rt)
                db.session.flush()
                db.session.add_all([
                    AirportFlightRoute(role=AirportRole.DEPARTURE, airport_id=dep_ap.id, flight_route_id=rt.id),
                    AirportFlightRoute(role=AirportRole.ARRIVAL, airport_id=arr_ap.id, flight_route_id=rt.id),
                ])
                return rt

            # 5. Khởi tạo 16 Tuyến bay (8 cặp khứ hồi đa hãng)
            route_vna_sgn_han = create_route("Sài Gòn - Hà Nội (VNA)", vna, sgn, han)
            route_vna_han_sgn = create_route("Hà Nội - Sài Gòn (VNA)", vna, han, sgn)

            route_vj_sgn_han = create_route("Sài Gòn - Hà Nội (VJ)", vj, sgn, han)
            route_vj_han_sgn = create_route("Hà Nội - Sài Gòn (VJ)", vj, han, sgn)

            route_vna_sgn_dad = create_route("Sài Gòn - Đà Nẵng (VNA)", vna, sgn, dad)
            route_vna_dad_sgn = create_route("Đà Nẵng - Sài Gòn (VNA)", vna, dad, sgn)

            route_vna_han_pqc = create_route("Hà Nội - Phú Quốc (VNA)", vna, han, pqc)
            route_vna_pqc_han = create_route("Phú Quốc - Hà Nội (VNA)", vna, pqc, han)

            route_vj_sgn_cxr = create_route("Sài Gòn - Nha Trang (VJ)", vj, sgn, cxr)
            route_vj_cxr_sgn = create_route("Nha Trang - Sài Gòn (VJ)", vj, cxr, sgn)

            route_vj_dad_hph = create_route("Đà Nẵng - Hải Phòng (VJ)", vj, dad, hph)
            route_vj_hph_dad = create_route("Hải Phòng - Đà Nẵng (VJ)", vj, hph, dad)

            route_bav_han_dli = create_route("Hà Nội - Đà Lạt (BAV)", bav, han, dli)
            route_bav_dli_han = create_route("Đà Lạt - Hà Nội (BAV)", bav, dli, han)

            route_vua_sgn_hui = create_route("Sài Gòn - Huế (VUA)", vua, sgn, hui)
            route_vua_hui_sgn = create_route("Huế - Sài Gòn (VUA)", vua, hui, sgn)

            # Hàm hỗ trợ tạo Chuyến bay (Flight) + các Chặng bay (FlightSegment + AirportFlightSegment)
            def create_flight(code, price_str, route_obj, airline_obj, seg_items):
                fl = Flight(
                    flight_code=code,
                    base_price=Decimal(price_str),
                    flight_route_id=route_obj.id,
                    airline_id=airline_obj.id
                )
                db.session.add(fl)
                db.session.flush()

                for idx, (dep_ap, arr_ap, plane_obj, dep_dt, arr_dt) in enumerate(seg_items, start=1):
                    seg = FlightSegment(
                        departure_time=dep_dt,
                        arrival_time=arr_dt,
                        sequence=idx,
                        flight_id=fl.id,
                        airplane_id=plane_obj.id
                    )
                    db.session.add(seg)
                    db.session.flush()
                    db.session.add_all([
                        AirportFlightSegment(role=AirportRole.DEPARTURE, airport_id=dep_ap.id, flight_segment_id=seg.id),
                        AirportFlightSegment(role=AirportRole.ARRIVAL, airport_id=arr_ap.id, flight_segment_id=seg.id),
                    ])
                return fl

            # Mốc ngày động tính từ hôm nay để chuyến bay luôn hợp lệ khi test
            base_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            d2 = base_day + timedelta(days=2)
            d3 = base_day + timedelta(days=3)
            d4 = base_day + timedelta(days=4)
            d5 = base_day + timedelta(days=5)
            d6 = base_day + timedelta(days=6)

            # 6 & 7 & 8. Khởi tạo 18 Chuyến bay đủ mọi kịch bản test
            # --- Cặp 1: Nối chuyến 1 trạm trung gian (SGN -> DAD -> HAN) & Khứ hồi (HAN -> DAD -> SGN / HAN -> SGN) ---
            create_flight("VN210", "2200000", route_vna_sgn_han, vna, [
                (sgn, dad, plane_vna_1, d2.replace(hour=7, minute=30), d2.replace(hour=8, minute=50)),
                (dad, han, plane_vna_2, d2.replace(hour=10, minute=0), d2.replace(hour=11, minute=20)),
            ])
            create_flight("VN211", "2200000", route_vna_han_sgn, vna, [
                (han, dad, plane_vna_2, d2.replace(hour=14, minute=30), d2.replace(hour=15, minute=50)),
                (dad, sgn, plane_vna_1, d2.replace(hour=16, minute=20), d2.replace(hour=17, minute=40)),
            ])
            create_flight("VN212", "1950000", route_vna_han_sgn, vna, [
                (han, sgn, plane_vna_1, d4.replace(hour=9, minute=0), d4.replace(hour=11, minute=10)),
            ])

            # --- Cặp 2: Bay thẳng Vietjet (SGN <-> HAN) ---
            create_flight("VJ120", "1500000", route_vj_sgn_han, vj, [
                (sgn, han, plane_vj_1, d2.replace(hour=9, minute=0), d2.replace(hour=11, minute=10)),
            ])
            create_flight("VJ121", "1550000", route_vj_han_sgn, vj, [
                (han, sgn, plane_vj_1, d3.replace(hour=16, minute=0), d3.replace(hour=18, minute=10)),
            ])

            # --- Cặp 3: Bay thẳng chặng ngắn (SGN <-> DAD) ---
            create_flight("VN115", "1200000", route_vna_sgn_dad, vna, [
                (sgn, dad, plane_vna_1, d2.replace(hour=14, minute=15), d2.replace(hour=15, minute=35)),
            ])
            create_flight("VN116", "1250000", route_vna_dad_sgn, vna, [
                (dad, sgn, plane_vna_1, d2.replace(hour=18, minute=0), d2.replace(hour=19, minute=20)),
            ])

            # --- Cặp 4: Nối chuyến 2 trạm trung gian tối đa (HAN -> VII -> HUI -> PQC) & Khứ hồi thẳng ---
            create_flight("VN301", "2600000", route_vna_han_pqc, vna, [
                (han, vii, plane_vna_1, d3.replace(hour=6, minute=30), d3.replace(hour=7, minute=25)),
                (vii, hui, plane_vna_1, d3.replace(hour=7, minute=50), d3.replace(hour=8, minute=40)),
                (hui, pqc, plane_vna_1, d3.replace(hour=9, minute=5), d3.replace(hour=10, minute=45)),
            ])
            create_flight("VN302", "2400000", route_vna_pqc_han, vna, [
                (pqc, han, plane_vna_2, d6.replace(hour=15, minute=0), d6.replace(hour=17, minute=10)),
            ])

            # --- Cặp 5: Sài Gòn <-> Nha Trang (Vietjet) ---
            create_flight("VJ602", "950000", route_vj_sgn_cxr, vj, [
                (sgn, cxr, plane_vj_2, d2.replace(hour=8, minute=0), d2.replace(hour=9, minute=10)),
            ])
            create_flight("VJ603", "980000", route_vj_cxr_sgn, vj, [
                (cxr, sgn, plane_vj_2, d4.replace(hour=15, minute=0), d4.replace(hour=16, minute=10)),
            ])

            # --- Cặp 6: Đà Nẵng <-> Hải Phòng (Vietjet) ---
            create_flight("VJ720", "1100000", route_vj_dad_hph, vj, [
                (dad, hph, plane_vj_1, d3.replace(hour=10, minute=0), d3.replace(hour=11, minute=25)),
            ])
            create_flight("VJ721", "1150000", route_vj_hph_dad, vj, [
                (hph, dad, plane_vj_1, d5.replace(hour=16, minute=0), d5.replace(hour=17, minute=25)),
            ])

            # --- Cặp 7: Hà Nội <-> Đà Lạt (Bamboo Airways) ---
            create_flight("QH1421", "1600000", route_bav_han_dli, bav, [
                (han, dli, plane_bav_1, d2.replace(hour=11, minute=0), d2.replace(hour=12, minute=50)),
            ])
            create_flight("QH1422", "1650000", route_bav_dli_han, bav, [
                (dli, han, plane_bav_1, d5.replace(hour=14, minute=0), d5.replace(hour=15, minute=50)),
            ])

            # --- Cặp 8: Sài Gòn <-> Huế (Vietravel Airlines) ---
            create_flight("VU510", "1050000", route_vua_sgn_hui, vua, [
                (sgn, hui, plane_vua_1, d3.replace(hour=8, minute=0), d3.replace(hour=9, minute=25)),
            ])
            create_flight("VU511", "1080000", route_vua_hui_sgn, vua, [
                (hui, sgn, plane_vua_1, d5.replace(hour=18, minute=0), d5.replace(hour=19, minute=25)),
            ])

            # --- Chuyến cận giờ bay (sau 6 tiếng: khóa đặt Online <12h, vẫn bán được tại quầy >4h) ---
            near_dep = datetime.now() + timedelta(hours=6)
            create_flight("VN999", "1200000", route_vna_sgn_dad, vna, [
                (sgn, dad, plane_vna_2, near_dep, near_dep + timedelta(hours=1, minutes=20)),
            ])

            # 9. Danh mục ghế dùng chung (10 ghế Thương gia A01-A10, 20 ghế Phổ thông B01-B20)
            seats = []
            for i in range(1, 11):
                seats.append(Seat(seat_number=f"A{i:02d}", seat_class=SeatClass.BUSINESS))
            for i in range(1, 21):
                seats.append(Seat(seat_number=f"B{i:02d}", seat_class=SeatClass.ECONOMY))
            db.session.add_all(seats)

            db.session.commit()
            print("Tạo dữ liệu mẫu thành công: 10 sân bay, 16 tuyến bay, 18 chuyến bay!")

        except Exception as e:
            db.session.rollback()
            print(f"Lỗi khởi tạo dữ liệu: {e}")


if __name__ == '__main__':
    with app.app_context():
        db.session.execute(text('SET FOREIGN_KEY_CHECKS = 0;'))
        for table_name in db.inspect(db.engine).get_table_names():
            db.session.execute(text(f'DROP TABLE IF EXISTS `{table_name}`;'))
        db.session.execute(text('SET FOREIGN_KEY_CHECKS = 1;'))
        db.session.commit()
        seed_flight_data()