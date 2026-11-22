from flask import render_template, request, redirect, url_for
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask_login import login_user, logout_user, login_required
from cloudinary.exceptions import Error as CloudinaryError
from eapp import app, dao, login, db


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


@app.route('/flightpage', methods=['GET', 'POST'])
def flight_page_view():
    airplane = dao.count_airplane()
    return render_template('flightpage.html', airplane=airplane)


@app.route('/search')
def flight_search():
    return redirect(url_for('home_view'))


@app.route('/register')
def register_view():
    return render_template('register.html')


@app.route('/register', methods=['POST'])
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
        except CloudinaryError as ex:
            print("LỖI CLOUDINARY:", ex)
            err_msg = 'Lỗi tải ảnh đại diện, vui lòng thử lại!'
        except IntegrityError as ex:
            db.session.rollback()
            print("LỖI TRÙNG DỮ LIỆU SQL:", ex)
            err_msg = 'Tên tài khoản hoặc số điện thoại đã tồn tại!'
        except SQLAlchemyError as ex:
            db.session.rollback()
            print("LỖI DATABASE SQL:", ex)
            err_msg = 'Lỗi kết nối cơ sở dữ liệu, vui lòng thử lại sau!'

    return render_template('register.html', err_msg=err_msg)


@app.route('/login')
def login_view():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
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