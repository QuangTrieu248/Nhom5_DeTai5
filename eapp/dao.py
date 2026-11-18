# from eapp import db
import hashlib
from eapp.models import Airport, db, Airplane, User
from eapp.models import Airport,db, Airplane

def load_airport():
    return Airport.query.all()

def count_airplane():
    return Airplane.query.count()

def add_user(name, username, password, avatar=None):
    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())
    u = User(
        name=name.strip(),
        username=username.strip(),
        password=password
    )
    if avatar:
        u.avatar = avatar

    db.session.add(u)
    db.session.commit()