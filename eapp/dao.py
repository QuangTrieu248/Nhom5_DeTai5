from eapp.models import Airport, Airplane, User, PhoneNumber, db
import cloudinary.uploader
import hashlib


def load_airports():
    return Airport.query.all()


def count_airplane():
    return Airplane.query.count()


def get_user_by_id(user_id):
    return User.query.get(int(user_id))


def get_user_by_username(username):
    if not username:
        return None
    return User.query.filter(User.username.__eq__(username.strip())).first()


def get_phone_number(phone):
    if not phone:
        return None
    return PhoneNumber.query.filter(PhoneNumber.number.__eq__(phone.strip())).first()


def check_login(username, password):
    if not username or not password:
        return None
    password = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())
    return User.query.filter(
        User.username.__eq__(username.strip()),
        User.password.__eq__(password)
    ).first()


def add_user(name, username, password, phone=None, avatar=None):
    password = hashlib.md5(password.strip().encode('utf-8')).hexdigest()
    u = User(
        name=name.strip(),
        username=username.strip(),
        password=password
    )
    if avatar and avatar.filename != '':
        res = cloudinary.uploader.upload(avatar)
        u.avatar = res.get('secure_url')

    db.session.add(u)

    if phone:
        p = PhoneNumber(number=phone.strip(), user=u)
        db.session.add(p)

    db.session.commit()