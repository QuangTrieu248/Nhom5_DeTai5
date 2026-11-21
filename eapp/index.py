from flask import render_template, request, redirect, url_for
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from cloudinary.exceptions import Error as CloudinaryError
from eapp import app, dao


@app.route('/')
def home_view():
    return render_template('homepage.html')


@app.route('/staffpage')
def staff_view():
    return render_template('staffpage.html')


# @app.route('/flightpage')
# def flight_page_view():
#     airport = dao.load_airport()
#     return render_template('flightpage.html', airport=airport)
@app.route('/flightpage')
def flight_page_view():
    airplane = dao.count_airplane()
    return render_template('flightpage.html', airplane=airplane)


@app.route('/search')
def flight_search():
    return render_template('homepage.html')


@app.route('/register')
def register_view():
    return render_template('register.html')


@app.route('/register', methods=['post'])
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
        except CloudinaryError:
            err_msg = 'Lỗi tải ảnh đại diện, vui lòng thử lại!'
        except IntegrityError:
            err_msg = 'Tên tài khoản hoặc số điện thoại đã tồn tại!'
        except SQLAlchemyError:
            err_msg = 'Lỗi kết nối cơ sở dữ liệu, vui lòng thử lại sau!'

    return render_template('register.html', err_msg=err_msg)


@app.route('/login')
def login_view():
    return render_template('login.html')


if __name__ == '__main__':
    app.run(debug=True)