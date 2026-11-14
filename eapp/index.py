from flask import Flask, render_template

app = Flask(__name__)
   # return render_template('homepage.html')

@app.route('/')
def home_view():
    return render_template('homepage.html')

@app.route('/trangnhanvien')
def hienThiTrangNhanVien():
    return render_template('staffpage.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)