# from eapp import db
from eapp.models import Airport,db, Airplane

def load_airport():
    return Airport.query.all()

def count_airplane():
    return Airplane.query.count()