from flask import render_template, request, redirect, url_for
from eapp import app, dao
import os
import uuid


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

@app.route('/register', methods=['get', 'post'])
def register_view():
    err_msg = None
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            err_msg = 'Mật khẩu xác nhận không khớp!'
        else:
            name = request.form.get('fullname')
            username = request.form.get('username')
            avatar_file = request.files.get('avarta')
            avatar_path = None

            if avatar_file and avatar_file.filename != '':
                ext = os.path.splitext(avatar_file.filename)[1]
                filename = f"{uuid.uuid4().hex}{ext}"
                upload_dir = os.path.join(app.root_path, 'static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                avatar_file.save(os.path.join(upload_dir, filename))
                avatar_path = f'/static/uploads/{filename}'

            try:
                dao.add_user(
                    name=name,
                    username=username,
                    password=password,
                    avatar=avatar_path
                )
                return redirect(url_for('login_view'))
            except Exception:
                err_msg = 'Tên đăng nhập đã tồn tại hoặc dữ liệu không hợp lệ!'

    return render_template('register.html', err_msg=err_msg)
@app.route('/login')
def login_view():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)

    