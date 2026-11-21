from eapp.models import db, Airplane, Airport, Flight, FlightSegment,Policy, Airline, AirportFlightRoute,FlightRoute, AirportRole
from sqlalchemy import func
from sqlalchemy.orm import aliased

from eapp import app

# Ham dau tien, test thu
def load_flight_tickect():
    query = (db.session.query(Airplane.airline_name,Flight.flight_code,FlightSegment.departure_time,FlightSegment.arrival_time))
    return query.all()

def load_test_query():
    f = Flight.query.get(1)
    f.segments_relation().get()
    print(f)

def load_flight_tickect1():
    query = (
        db.session.query(
            Airplane.airline_name,
            Flight.flight_code,
            FlightSegment.departure_time,
            FlightSegment.arrival_time
        )
        .select_from(FlightSegment)
        .join(Airplane, FlightSegment.airplane_id == Airplane.id)
        .join(Flight, FlightSegment.flight_id == Flight.id)
    )
    return query.all()



def load_flight_tickect2():
    query = (
        db.session.query(
            Flight.id,
            Flight.flight_code,
            Airplane.airline_name,
            func.min(FlightSegment.departure_time).label('departure_time'),
            func.max(FlightSegment.arrival_time).label('arrival_time')
        )
        .select_from(Flight)
        .join(FlightSegment, FlightSegment.flight_id == Flight.id)
        .join(Airplane, FlightSegment.airplane_id == Airplane.id)
        .group_by(Flight.id, Flight.flight_code, Airplane.airline_name)
    )
    return query.all()

def load_flight_tickect3():
    # Tạo bí danh (alias) để join bảng Airport và AirportFlightRoute 2 lần (1 cho điểm đi, 1 cho điểm đến)
    DepRouteAirport = aliased(AirportFlightRoute)
    ArrRouteAirport = aliased(AirportFlightRoute)
    DepAirport = aliased(Airport)
    ArrAirport = aliased(Airport)

    query = (
        db.session.query(
            Flight.id,
            Flight.flight_code,
            Airline.name.label('airline_name'),
            FlightRoute.name.label('route_name'),
            DepAirport.name.label('departure_airport'),
            ArrAirport.name.label('arrival_airport'),
            func.min(FlightSegment.departure_time).label('departure_time'),
            func.max(FlightSegment.arrival_time).label('arrival_time'),
            func.count(FlightSegment.id).label('total_segments') # Đếm số chặng (1 = bay thẳng, >1 = có trung chuyển)
        )
        .select_from(Flight)
        .join(Airline, Flight.airline_id == Airline.id)
        .join(FlightRoute, Flight.flight_route_id == FlightRoute.id)
        .join(FlightSegment, FlightSegment.flight_id == Flight.id)
        # Join lấy sân bay khởi hành (DEPARTURE) của tuyến bay
        .join(DepRouteAirport, (DepRouteAirport.flight_route_id == FlightRoute.id) & (DepRouteAirport.role == AirportRole.DEPARTURE))
        .join(DepAirport, DepRouteAirport.airport_id == DepAirport.id)
        # Join lấy sân bay đích (ARRIVAL) của tuyến bay
        .join(ArrRouteAirport, (ArrRouteAirport.flight_route_id == FlightRoute.id) & (ArrRouteAirport.role == AirportRole.ARRIVAL))
        .join(ArrAirport, ArrRouteAirport.airport_id == ArrAirport.id)
        .group_by(
            Flight.id,
            Flight.flight_code,
            Airline.name,
            FlightRoute.name,
            DepAirport.name,
            ArrAirport.name
        )
    )
    return query.all()


def get_flights():
    flights = (
        db.session.query(
            Flight.id.label("id"),
            Airline.name.label("airline_name"),
            Flight.flight_code.label("flight_code"),
            func.min(FlightSegment.departure_time).label("departure_time"),
            func.max(FlightSegment.arrival_time).label("arrival_time"),
            Flight.base_price.label("base_price"),
        )
        .join(Airline, Flight.airline_id == Airline.id)
        .join(FlightSegment, Flight.id == FlightSegment.flight_id)
        .group_by(
            Flight.id, Airline.name, Flight.flight_code, Flight.base_price
        )
        .order_by(func.min(FlightSegment.departure_time).asc())
        .all()
    )
    return flights

####
if __name__ == '__main__':
   with app.app_context():
       load_test_query()