import json
import random
import string

import bcrypt
from flask import (Flask, render_template, g, send_from_directory, flash)
from flask import jsonify
from flask import request, session, redirect, url_for, escape
import os

from werkzeug.utils import secure_filename

import dbclient
from util import get_file_extension, load_config

app = Flask(__name__)
app.secret_key = load_config()["flask"]["password"].encode()
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'db'):
        g.db = dbclient.MyClient(app.root_path)
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


ALLOWED_EXTENSIONS = tuple('jpg jpe jpeg png webp webm mp4'.split())


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# path has to have a trailing slash /
def generate_unique_filename(path):
    filename = ''.join(random.choices(string.ascii_lowercase, k=15))
    if os.path.isfile(path + filename):
        return generate_unique_filename(path)
    else:
        return filename


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if logged_in() and request.method == 'POST' and 'photo' in request.files and 'title' in request.form:
        file = request.files['photo']
        # _, file_extension = os.path.splitext(file.filename)
        if get_file_extension(file.filename) not in ALLOWED_EXTENSIONS:
            return "that filetype is not allowed"

        """
        img = Image.open(app.root_path + "/uploads/"+filename)
        img.thumbnail((900,1750))
        filename, file_extension = os.path.splitext(filename)
        new_filename = filename+".webp"
        img.save(app.root_path + "/uploads/"+new_filename,format="WEBP")
        os.remove(app.root_path +"/uploads/"+filename+ file_extension)
        get_db().send_pic(new_filename, current_user())
        """

        get_db().send_pic(file, current_user(), get_file_extension(file.filename), request.form['title'],
                          request.form.get('show_username', None))

        return render_template('upload.html')
    elif logged_in():
        return render_template('upload.html')
    else:
        return "you not logged in brotha"


def create_thumbnail(filename):
    if not os.path.isfile(f"{app.root_path}/thumbnails/{filename}.webp"):
        os.system(
            f"ffmpeg -i {app.root_path}/uploads/{filename} -ss 00:00:00.000 -vframes 1 {app.root_path}/thumbnails/{filename}.webp")


def get_url_to_file(directory, filename):
    if __name__ == "__main__":
        return url_for(directory, filename=filename, _external=True)
    else:
        return f"https://tgag.app/{directory}/{filename}"


def get_thumbnail_url(filename):
    create_thumbnail(filename)
    return get_url_to_file("thumbnails", filename + ".webp")


@app.route('/thumbnails/<filename>', methods=['GET'])
def thumbnails(filename):
    return send_from_directory(f'{app.root_path}/thumbnails', filename, as_attachment=False,
                                   mimetype='image')


@app.route('/uploads/<filename>', methods=['GET'])
def uploads(filename):
    return send_from_directory(f'{app.root_path}/uploads', filename, as_attachment=False)


def get_better_upload_overview(userID):
    users_uploads = get_db().get_upload_overview(current_user())
    uploads_with_info = []
    for (itemID, filename, rating) in users_uploads:
        info = get_item_info(itemID)
        info["rating"] = rating
        uploads_with_info += [info]
    return uploads_with_info


@app.route('/your_memes', methods=['GET'])
def your_memes():
    if logged_in():
        return render_template('show_uploads.html', uploads=get_better_upload_overview(current_user()))
    else:
        return "you not logged in brotha"


@app.route('/my_uploads_app', methods=['GET'])
def my_uploads_app():
    if logged_in():
        # users_uploads = get_db().get_upload_overview(current_user())

        # uploads_with_urls = [{ "itemID": itemID, "url": photos.url(filename), "rating" : rating } for (itemID, filename, rating) in users_uploads]
        return jsonify({"my_uploads": get_better_upload_overview(current_user())})
    else:
        return "you not logged in brotha", 500


@app.route('/top_json')
def top_json():
    if logged_in():
        top = get_db().get_top_n(current_user())
        return jsonify({"top_rec": top})
    else:
        return "Error", 500


def file_extension(filename):
    _, file_extension = os.path.splitext(filename)
    return file_extension[1:]


def meme_type(filename):
    ext = file_extension(filename)
    if ext == "mp4" or ext == "webm":
        return "video"
    else:
        return "image"


def get_item_info(itemID):
    pic = get_db().get_pic(itemID)
    filename = pic["filename"]
    t = meme_type(filename)
    ext = file_extension(filename)
    if t == "video":
        thumb = get_thumbnail_url(filename)
    else:
        thumb = None

    author = None
    if pic["show_username"]:
        author = pic["username"]
    return {"itemID": itemID, "url": get_url_to_file("uploads", pic["filename"]), "author": author,
            "file_extension": ext,
            "type": t, "filename": filename, "thumbnail_url": thumb, "title": pic["title"]}


@app.route('/top_urls_json')
def top_urls_json():
    if logged_in():
        top = get_db().get_top_n(current_user(), 20)
        urls = [get_item_info(itemID) for itemID in top]
        return jsonify({"top_rec": urls})
    else:
        return "Error", 500


@app.route('/', methods=['GET'])
def home():
    if logged_in():
        top = get_db().get_top_n(current_user())
        if top:
            itemID = top[0]
            pic = get_db().get_pic(itemID)
            filename = pic["filename"]
            url = get_url_to_file("uploads", filename)
            if pic["show_username"]:
                author = pic["username"]
            else:
                author = None
            return render_template('home.html', memeID=itemID, memeurl=url, m_type=meme_type(filename),
                                   title=pic["title"], author=author)
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
            get_db().add_user(u, p, False)
            session['username'] = u
            return jsonify()
        else:
            return jsonify(), 500
    else:
        return jsonify(), 400


@app.route('/merge_app_user', methods=['POST'])
def merge_app_user():
    ou = request.json['old_username']
    u = request.json['username']
    p = request.json['password']
    if len(u) < 30 or len(p) < 30:
        if not user_exists(u) and user_exists(ou):
            get_db().merge_user(u, p, ou)
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
