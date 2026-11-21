from flask import render_template, request, redirect, url_for
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask_login import login_user, logout_user
from cloudinary.exceptions import Error as CloudinaryError
from eapp import app, dao, login


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

@app.route('/login')
def login_view():
    return render_template('login.html')


@app.route('/login', methods=['post'])
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
def logout_view():
    logout_user()
    return redirect(url_for('login_view'))


if __name__ == '__main__':
    app.run(debug=True)

    