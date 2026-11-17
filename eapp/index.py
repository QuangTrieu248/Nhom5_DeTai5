from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home_view():
    return render_template('homepage.html')

@app.route('/staffpage')
def staff_view():
    return render_template('staffpage.html')

@app.route('/search')
def search():
    return render_template('search.html')

@app.route('/register')
def register_view():
    return render_template('register.html')

@app.route('/login')
def login_view():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)