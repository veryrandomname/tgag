import bcrypt
from flask import (Flask, render_template, g, send_from_directory)
from flask import jsonify
from flask import request, session, redirect, url_for, escape
from flask_uploads import (UploadSet, configure_uploads, patch_request_class, UploadConfiguration, IMAGES)
from PIL import Image
import os
import dbclient

app = Flask(__name__)
app.secret_key = b'as90dhjaSJAaAsafgAF6a6aa36as4DA1'
if __name__ != "__main__":
    app.config['SERVER_NAME'] = "tgag.app:80"
patch_request_class(app, 1024 * 1024 * 10)  # 10MB file size max


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


ALLOWED_EXTENSIONS = tuple('jpg jpe jpeg png webp webm mp4'.split())
photos = UploadSet('photos', default_dest=lambda app: app.root_path + "/uploads", extensions=ALLOWED_EXTENSIONS)
if __name__ != "__main__":
    photos._config = UploadConfiguration(app.root_path + "/uploads", base_url="https://tgag.app/_uploads/photos/")
configure_uploads(app, photos)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if logged_in() and request.method == 'POST' and 'photo' in request.files:
        filename = photos.save(request.files['photo'])

        name, extension = os.path.splitext(filename)
        if extension == "webm" or extension == "mp4":
            create_thumbnail(filename)
        """
        img = Image.open(app.root_path + "/uploads/"+filename)
        img.thumbnail((900,1750))
        filename, file_extension = os.path.splitext(filename)
        new_filename = filename+".webp"
        img.save(app.root_path + "/uploads/"+new_filename,format="WEBP")
        os.remove(app.root_path +"/uploads/"+filename+ file_extension)
        get_db().send_pic(new_filename, current_user())
        """
        get_db().send_pic(filename, current_user())

        return render_template('upload.html')
    elif logged_in():
        return render_template('upload.html')
    else:
        return "you not logged in brotha"


def create_thumbnail(filename):
    if not os.path.isfile(f"{app.root_path}/thumbnails/{filename}.webp"):
        os.system(f"ffmpeg -i {app.root_path}/uploads/{filename} -ss 00:00:00.000 -vframes 1 {app.root_path}/thumbnails/{filename}.webp")


def get_thumbnail_url(filename):
    create_thumbnail(filename)

    return url_for('thumbnails', filename=filename, _external=True)


@app.route('/thumbnails/<filename>', methods=['GET'])
def thumbnails(filename):
    return send_from_directory(f'{app.root_path}/thumbnails', filename + ".webp", as_attachment = False, mimetype='image')


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
    thumb = get_thumbnail_url(filename)
    return {"itemID": itemID, "url": photos.url(pic["filename"]), "author": pic["username"], "file_extension": ext,
            "type": t, "filename": filename, "thumbnail_url" : thumb}


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
            filename = get_db().get_pic(itemID)["filename"]
            url = photos.url(filename)
            return render_template('home.html', memeID=itemID, memeurl=url, m_type=meme_type(filename))
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
