from flask import (Flask,request,render_template,g)

from flask import request, session, redirect, url_for, escape

from flask import jsonify

from flask_uploads import (UploadSet,configure_uploads)
import dbclient as db
app = Flask(__name__)

app.secret_key = b'yu8Qy4xkBdCvMSJQiZG8k3Vbdv4GUf'

DATABASE = '/path/to/database.db'



def user_exists(username):
    return bool(db.get_user(username))


def check_password(username, password):
    hashed_password = db.get_user(username)['password']  # .encode('utf-8')
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)


def logged_in():
    return session['username'] is not None

def current_user():
    return session['username']


@app.teardown_appcontext
def close_connection(exception):
    db.tear_down_connection()

photos = UploadSet('photos', default_dest=lambda app: app.instance_path)
configure_uploads(app,photos)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST' and 'photo' in request.files:
        filename = photos.save(request.files['photo'])
        db.send_pic(filename)
        return "upload successfull"
    return render_template('upload.html') 

@app.route('/photo/<id>')
def show(id):
    photo = db.get_pic(id)
    if photo is None:
        abort(404)
    url = photos.url(photo.filename)
    return render_template('show.html', url=url, photo=photo)


@app.route('/', methods=['GET'])
def home():
    return render_template('home.html', popular=front_page_opinions())


@app.route('/opinion/<oid_str>')
def opinion(oid_str):
    if oid_str:
        return render_opinion(int(oid_str))
    else:
        return render_template('home.html')


@app.route('/new_opinion/', methods=['GET', 'POST'])
def new_opinion():
    if request.method == 'POST' and logged_in():
        text = request.form['text']
        oid = add_opinion(text, current_user())
        vote_opinion(oid, 1, current_user())
        if oid:
            return redirect(url_for('opinion', oid_str=oid))
        else:
            return "Your opinion is too long. max. " + str(OPINION_LENGTH) + " signs."
    else:
        return render_template("new_opinion.html")


@app.route('/vote_opinion/', methods=['POST'])
def vote_opinion_handler():
    oid = int(request.form['oid'])
    vote = int(request.form['vote'])
    if logged_in():
        vote_opinion(oid, vote, current_user())
        return "suckcess"
    else:
        return "not logged in, bitch"




@app.route('/check')
def check_login():
    if logged_in():
        return 'Logged in as %s' % escape(session['username'])
    return 'You are not logged in'


@app.route('/new_user', methods=['GET', 'POST'])
def new_user():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        if len(u) < 30 or len(p) < 30:
            if user_exists(u):
                db.add_user(u, p)
                session['username'] = u
                return redirect(url_for('home'))
            else:
                return "username already taken"
        else:
            return "username or password are longer than 30 signs"
    return render_template("new_user.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        if check_password(u, p):
            session['username'] = u
            return redirect(url_for('home'))
        else:
            return "something went wrong"
    return render_template("login.html")


@app.route('/logout')
def logout():
    # remove the username from the session if it's there
    session.pop('username', None)
    return redirect(url_for('home'))


@app.route('/about', methods=['GET'])
def about():
    return render_template("about.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")