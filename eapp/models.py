import datetime
from enum import Enum as UserEnum
from enum import Enum as AirEnum
from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.orm import relationship
from eapp import db, app


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
    avatar = Column(String(255), default='/static/user_account.png')
    username = Column(String(50), nullable=False, unique=True)
    password = Column(String(100), nullable=False)
    user_role = Column(Enum(UserRole), default=UserRole.USER)
    phone_numbers = relationship('PhoneNumber', backref='user', lazy=True)

    def __str__(self):
        return self.name


class PhoneNumber(BaseModel):
    __tablename__ = 'phone_number'

    number = Column(String(15), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)

    def __str__(self):
        return self.number


# PHẦN CHUYẾN BAY
class AirportRole(AirEnum):
    DEPARTURE = 1
    ARRIVAL = 2


class Airport(BaseModel):
    name = Column(String(100), nullable=False)
    address = Column(String(500), nullable=False)

    def __str__(self):
        return self.name


class Airplane(BaseModel):
    airline_name = Column(String(100), nullable=False)
    number_seat = Column(Integer, nullable=False)
    segments_relation = relationship('FlightSegment', backref='airplane', lazy=True)

    def __str__(self):
        return self.airline_name


class FlightRoute(BaseModel):
    name = Column(String(100), nullable=False)
    flights_relation = relationship('Flight', backref='flight_route', lazy=True)
    airport_relation = relationship('AirportFlightRoute', backref='flight_route', lazy=True)


class AirportFlightRoute(BaseModel):
    role = Column(Enum(AirportRole), default=AirportRole.DEPARTURE, nullable=False)
    airport_id = Column(Integer, ForeignKey(Airport.id), nullable=False)
    flight_route_id = Column(Integer, ForeignKey(FlightRoute.id), nullable=False)


class Flight(BaseModel):
    flight_code = Column(String(10), unique=True, nullable=False)
    flight_route_id = Column(Integer, ForeignKey(FlightRoute.id), nullable=False)
    segments_details = relationship('FlightSegment', backref='flight', lazy=True)


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
    )


class AirportFlightSegment(BaseModel):
    role = Column(Enum(AirportRole), default=AirportRole.DEPARTURE, nullable=False)
    airport_id = Column(Integer, ForeignKey(Airport.id), nullable=False)
    flight_segment_id = Column(Integer, ForeignKey(FlightSegment.id), nullable=False)


if __name__ == '__main__':
    with app.app_context():
        db.drop_all()
        db.create_all()

        # 1. Tạo dữ liệu Sân bay, Máy bay và Tuyến bay
        sgn = Airport(name='Sân bay Quốc tế Tân Sơn Nhất', address='Trường Sơn, Tân Bình, TP.HCM')
        tpe = Airport(name='Sân bay Quốc tế Đào Viên', address='Đào Viên, Đài Loan')
        nrt = Airport(name='Sân bay Quốc tế Narita', address='Narita, Chiba, Nhật Bản')

        plane1 = Airplane(airline_name='Vietnam Airlines', number_seat=300)
        plane2 = Airplane(airline_name='Vietject Air', number_seat=180)

        route1 = FlightRoute(name='TP.HCM - Tokyo (Quá cảnh Đài Bắc)')

        db.session.add_all([sgn, tpe, nrt, plane1, plane2, route1])
        db.session.flush()

        # 2. Gắn sân bay đầu - cuối cho Tuyến bay
        route_dep = AirportFlightRoute(role=AirportRole.DEPARTURE, airport_id=sgn.id, flight_route_id=route1.id)
        route_arr = AirportFlightRoute(role=AirportRole.ARRIVAL, airport_id=nrt.id, flight_route_id=route1.id)

        # 3. Tạo Chuyến bay cụ thể
        flight1 = Flight(flight_code='VN300', flight_route_id=route1.id)
        db.session.add_all([route_dep, route_arr, flight1])
        db.session.flush()

        # 4. Tạo 2 Chặng bay (Segments) cho chuyến bay VN300
        seg1 = FlightSegment(
            departure_time=datetime.datetime(2026, 12, 1, 8, 0),
            arrival_time=datetime.datetime(2026, 12, 1, 12, 30),
            sequence=1,
            flight_id=flight1.id,
            airplane_id=plane1.id
        )
        seg2 = FlightSegment(
            departure_time=datetime.datetime(2026, 12, 1, 14, 0),
            arrival_time=datetime.datetime(2026, 12, 1, 18, 15),
            sequence=2,
            flight_id=flight1.id,
            airplane_id=plane2.id
        )
        db.session.add_all([seg1, seg2])
        db.session.flush()

        # 5. Gắn sân bay đi - đến cho từng Chặng bay
        seg1_dep = AirportFlightSegment(role=AirportRole.DEPARTURE, airport_id=sgn.id, flight_segment_id=seg1.id)
        seg1_arr = AirportFlightSegment(role=AirportRole.ARRIVAL, airport_id=tpe.id, flight_segment_id=seg1.id)

        seg2_dep = AirportFlightSegment(role=AirportRole.DEPARTURE, airport_id=tpe.id, flight_segment_id=seg2.id)
        seg2_arr = AirportFlightSegment(role=AirportRole.ARRIVAL, airport_id=nrt.id, flight_segment_id=seg2.id)

        db.session.add_all([seg1_dep, seg1_arr, seg2_dep, seg2_arr])
        db.session.commit()