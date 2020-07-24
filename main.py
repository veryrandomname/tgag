import os

from flask import (Flask,request,render_template,g)

from flask import request, session, redirect, url_for, escape

import bcrypt

from flask import jsonify

from flask_uploads import (UploadSet,configure_uploads)
import dbclient
app = Flask(__name__)

app.secret_key = b'yu8Qy4xkBdCvMSJQiZG8k3Vbdv4GUf'


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'db'):
        g.db = dbclient.MyClient()
    return g.db

def user_exists(username):
    return bool(get_db().get_user(username))


def check_password(username, password):
    user = get_db().get_user(username)  # .encode('utf-8')
    return user and bcrypt.checkpw(password.encode('utf-8'), user["hashed_password"])


def logged_in():
    return 'username' in session

app.jinja_env.globals.update(logged_in=logged_in)


def current_user():
    return session['username']


@app.teardown_appcontext
def close_db(exception):
    if hasattr(g, 'db'):
        g.db.tear_down_connection()

photos = UploadSet('photos', default_dest=lambda app: app.root_path + "/uploads")
configure_uploads(app,photos)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST' and 'photo' in request.files:
        filename = photos.save(request.files['photo'])
        get_db().send_pic(filename)
        return "upload successfull"
    return render_template('upload.html') 

@app.route('/photo/<id>')
def show(id):
    photo = get_db().get_pic(id)
    if photo is None:
        abort(404)
    url = photos.url(photo)
    return render_template('show.html', url=url, itemID=id)


@app.route('/', methods=['GET'])
def home():
    if logged_in():
        top = get_db().get_top_n(current_user())
        print(top)
        if top:
            itemID = top[0]
            print(itemID)
            filename = get_db().get_pic(itemID)
            print(filename)
            url = photos.url(filename)
            return render_template('home.html', memeID = itemID, memeurl = url )
        else:
            return render_template('home.html' )
    else:
        return render_template("home.html")
    #return render_template('home.html', popular=front_page_opinions())



@app.route('/vote_opinion/', methods=['POST'])
def vote_opinion_handler():
    oid = int(request.form['oid'])
    vote = int(request.form['vote'])
    if logged_in():
        vote_opinion(oid, vote, current_user())
        return "suckcess"
    else:
        return "not logged in, bitch"


@app.route('/rate_meme/', methods=['POST'])
def rating_handler():
    itemID = int(request.form['itemID'])
    rating = int(request.form['rating'])
    if logged_in():
        get_db().send_rating(itemID, rating, current_user())
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
            if not user_exists(u):
                get_db().add_user(u, p)
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
