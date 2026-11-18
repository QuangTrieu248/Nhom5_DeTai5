from eapp.models import Airport,db, Airplane

def count_airplane():
    return Airplane.query.all()


