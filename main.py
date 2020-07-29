import bcrypt
from flask import (Flask, render_template, g)
from flask import jsonify
from flask import request, session, redirect, url_for, escape
from flask_uploads import (UploadSet, configure_uploads, patch_request_class, UploadConfiguration)
from PIL import Image
import os
import dbclient

app = Flask(__name__)
app.secret_key = b'as90dhjaSJAaAsafgAF6a6aa36as4DA1'



patch_request_class(app,1024 * 1024) #1MB file size max

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
if __name__ != "__main__":
    photos._config = UploadConfiguration(app.root_path + "/uploads", base_url="http://18.195.83.66/" )
configure_uploads(app, photos)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if logged_in() and request.method == 'POST' and 'photo' in request.files:
        filename = photos.save(request.files['photo'])

        img = Image.open(app.root_path + "/uploads/"+filename)
        img.thumbnail((300,450))
        filename, file_extension = os.path.splitext(filename)
        filename = filename+".webp"
        img.save(app.root_path + "/uploads/"+filename,format="WEBP")

        get_db().send_pic(filename, current_user())
        return render_template('upload.html')
    elif logged_in():
        return render_template('upload.html')
    else:
        return "you not logged in brotha"


@app.route('/your_memes', methods=['GET'])
def your_memes():
    if logged_in():
        users_uploads = get_db().get_upload_overview(current_user())

        uploads_with_urls = [(itemID, photos.url(filename), rating) for (itemID, filename, rating) in users_uploads]
        return render_template('show_uploads.html', uploads=uploads_with_urls)
    else:
        return "you not logged in brotha"


@app.route('/top_json')
def top_json():
    if logged_in():
        top = get_db().get_top_n(current_user())
        return jsonify({"top_rec": top})
    else:
        return "Error", 500


@app.route('/top_urls_json')
def top_urls_json():
    if logged_in():
        top = get_db().get_top_n(current_user(), 20)
        urls = []
        for itemID in top:
            pic = get_db().get_pic(itemID)
            urls.append([itemID, photos.url(pic["filename"]), pic["username"]])
        return jsonify({"top_rec": urls})
    else:
        return "Error", 500

@app.route('/', methods=['GET'])
def home():
    if logged_in():
        top = get_db().get_top_n(current_user())
        if top:
            itemID = top[0]
            filename = get_db().get_pic(itemID)["filename"]
            url = photos.url(filename)
            return render_template('home.html', memeID=itemID, memeurl=url)
        else:
            return render_template('home.html')
    else:
        return render_template("home.html")
    # return render_template('home.html', popular=front_page_opinions())


@app.route('/rate_meme', methods=['POST'])
def rating_handler():
    itemID = int(request.form['itemID'])
    rating = int(request.form['rating'])
    if logged_in():
        get_db().send_rating(itemID, rating, current_user())
        return "suckcess"
    else:
        return "not logged in, bitch"


@app.route('/rate_meme_app', methods=['POST'])
def rating_app_handler():
    itemID = int(request.json['itemID'])
    rating = int(request.json['rating'])
    if logged_in():
        get_db().send_rating(itemID, rating, current_user())
        return jsonify()
    else:
        return jsonify(), 400


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


@app.route('/new_app_user', methods=['POST'])
def new_app_user():
    u = request.json['username']
    p = request.json['password']
    if len(u) < 30 or len(p) < 30:
        if not user_exists(u):
            get_db().add_user(u, p)
            session['username'] = u
            return jsonify()
        else:
            return jsonify(), 500
    else:
        return jsonify(), 400


@app.route('/login_app', methods=['POST'])
def login_app():
    u = request.json['username']
    p = request.json['password']
    if check_password(u, p):
        session['username'] = u
        return jsonify()
    else:
        return jsonify(), 400


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



if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
