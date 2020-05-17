# coding=utf-8
import bcrypt
from flask import Flask

from flask import render_template
from flask import request, session, redirect, url_for, escape

from flask import jsonify

from neo4j import GraphDatabase
import time

app = Flask(__name__)

OPINION_LENGTH = 200
COLOR_1 = (149, 175, 92)
COLOR_2 = (148, 118, 168)
COLOR_3 = "rgb(0, 0, 0)"
COLOR_4 = "rgb(255, 255, 255)"
COLOR_5 = "rgb(193, 193, 193)"

app.jinja_env.globals.update(OPINION_LENGTH=OPINION_LENGTH)
app.jinja_env.globals.update(COLOR_3=COLOR_3)
app.jinja_env.globals.update(COLOR_4=COLOR_4)
app.jinja_env.globals.update(COLOR_5=COLOR_5)

database = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "f9C6gE7zKeq3pJu"))


def add_user(username, password):
    salt = bcrypt.gensalt(12)
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    with database.session() as db_session:
        db_session.run("CREATE(: User {username: $username, password: $password} )",
                       username=username, password=hashed_password)


def get_user(username):
    with database.session() as db_session:
        return db_session.run("MATCH(u : User {username: $username} )"
                              "RETURN u",
                              username=username)


def user_exists(username):
    return bool(get_user(username))


def check_password(username, password):
    with database.session() as db_session:
        result = db_session.run("MATCH (u:User { username : $username} )"
                                "RETURN u",
                                username=username)
        user = result.single()['u']
        hashed_password = user['password']  # .encode('utf-8')
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password)


def add_opinion(text, username):
    if len(text) <= OPINION_LENGTH + text.count('\r\n'):
        with database.session() as db_session:
            o = db_session.run("MATCH (u : User { username : $username })"
                               "MATCH (c : Counter)"
                               "SET c.count = c.count + 1 "
                               "CREATE (o : Opinion {oid: c.count, text: $text })"
                               "CREATE (u)-[:CREATED]->(o)"
                               "RETURN o",
                               username=username, text=text)
            return o.single()['o']['oid']
    else:
        return None


def vote_opinion(oid, vote, username):
    if vote == -1 or vote == 1 or vote == 0:
        with database.session() as db_session:
            r = get_opinion_vote(oid, username)
            if r != 0:
                if r == vote:
                    db_session.run("MATCH (u : User { username: $username})"
                                   "MATCH (o:Opinion { oid: $oid })"
                                   "MATCH (u)-[v:VOTED]->(o)"
                                   "DELETE v",
                                   oid=oid, username=username, vote=vote)
                else:
                    db_session.run("MATCH (u : User { username: $username})"
                                   "MATCH (o:Opinion { oid: $oid })"
                                   "MATCH (u)-[v:VOTED]->(o)"
                                   "SET v.vote = $vote",
                                   oid=oid, username=username, vote=vote)
            else:
                db_session.run("MATCH (u : User { username: $username})"
                               "MATCH (o:Opinion { oid: $oid })"
                               "CREATE (u)-[:VOTED {vote : $vote}]->(o)",
                               oid=oid, username=username, vote=vote)


def add_implication(a, b, username):
    with database.session() as db_session:
        r = db_session.run("MATCH (a:Opinion { oid: $a_oid })"
                           "MATCH (b:Opinion { oid: $b_oid })"
                           "MERGE (a)-[:IMPLICATION]->(i:Implication)-[:IMPLICATION]->(b)"
                           "RETURN i",
                           a_oid=a, b_oid=b)
        return r.single()['i']


def vote_implication(a, b, username, vote):
    with database.session() as db_session:
        r = get_implication_vote(a, b, username)
        if r != 0:
            if r == vote:
                db_session.run("MATCH (a:Opinion { oid: $a_oid })"
                               "MATCH (b:Opinion { oid: $b_oid })"
                               "MATCH (a)-[:IMPLICATION]->(i:Implication)-[:IMPLICATION]->(b)"
                               "MATCH (u : User { username: $username})"
                               "MATCH (u)-[v:VOTED_IMPLICATION ]->(i)"
                               "DELETE v",
                               a_oid=a, b_oid=b, username=username)
            else:
                db_session.run("MATCH (a:Opinion { oid: $a_oid })"
                               "MATCH (b:Opinion { oid: $b_oid })"
                               "MATCH (a)-[:IMPLICATION]->(i:Implication)-[:IMPLICATION]->(b)"
                               "MATCH (u : User { username: $username})"
                               "MATCH (u)-[v:VOTED_IMPLICATION ]->(i)"
                               "SET v.vote = $vote",
                               a_oid=a, b_oid=b, username=username, vote=vote)
        else:
            db_session.run("MATCH (a:Opinion { oid: $a_oid })"
                           "MATCH (b:Opinion { oid: $b_oid })"
                           "MATCH (a)-[:IMPLICATION]->(i:Implication)-[:IMPLICATION]->(b)"
                           "MATCH (u : User { username: $username})"
                           "CREATE (u)-[v:VOTED_IMPLICATION {vote: $vote} ]->(i)",
                           a_oid=a, b_oid=b, username=username, vote=vote)


def get_opinion_vote(oid, username):
    with database.session() as db_session:
        o = db_session.run("MATCH (u : User { username : $username})"
                           "MATCH (u)-[v :VOTED]->(o : Opinion { oid: $oid})"
                           "RETURN v.vote as vote",
                           username=username, oid=oid).single()
        if o:
            return o['vote']
        else:
            return 0


def get_implication_vote(a, b, username):
    with database.session() as db_session:
        r = db_session.run("MATCH (a:Opinion { oid: $a_oid })"
                           "MATCH (b:Opinion { oid: $b_oid })"
                           "MATCH (a)-[:IMPLICATION]->(i:Implication)-[:IMPLICATION]->(b)"
                           "MATCH (u : User { username: $username})"
                           "MATCH (u)-[v:VOTED_IMPLICATION ]->(i)"
                           "RETURN v.vote as vote",
                           a_oid=a, b_oid=b, username=username).single()
        if r:
            return r['vote']
        else:
            return 0


def get_implication_votes(a, b):
    with database.session() as db_session:
        r = db_session.run("MATCH (a:Opinion { oid: $a_oid })"
                           "MATCH (b:Opinion { oid: $b_oid })"
                           "MATCH (a)-[:IMPLICATION]->(i:Implication)-[:IMPLICATION]->(b)"
                           "MATCH (u)-[v:VOTED_IMPLICATION ]->(i)"
                           "RETURN v.vote as vote",
                           a_oid=a, b_oid=b)
        list_of_votes = [x['vote'] for x in r]
        return list_of_votes


def get_opinion_vote_current_user(o):
    if logged_in():
        return o['own_vote']
    else:
        return 0


def get_implication_vote_current_user(a, b):
    if logged_in():
        return get_implication_vote(a, b, current_user())
    else:
        return 0


def current_user_voted_opinion_1(oid):
    return get_opinion_vote_current_user(oid) > 0


def current_user_voted_opinion_minus_1(oid):
    return get_opinion_vote_current_user(oid) < 0


def current_user_voted_implication_1(a, b):
    return get_implication_vote_current_user(a, b) > 0


def current_user_voted_implication_minus_1(a, b):
    return get_implication_vote_current_user(a, b) < 0


app.jinja_env.globals.update(current_user_voted_opinion_1=current_user_voted_opinion_1)
app.jinja_env.globals.update(current_user_voted_opinion_minus_1=current_user_voted_opinion_minus_1)
app.jinja_env.globals.update(current_user_voted_implication_1=current_user_voted_implication_1)
app.jinja_env.globals.update(current_user_voted_implication_minus_1=current_user_voted_implication_minus_1)


def implication_number_of_pro_votes(a, b):
    return len([v for v in get_implication_votes(a, b) if v == 1])


def implication_number_of_con_votes(a, b):
    return len([v for v in get_implication_votes(a, b) if v == -1])


def implication_sum_of_votes(a, b):
    return sum(get_implication_votes(a, b))


def implication_stats(a, b):
    return implication_number_of_pro_votes(a, b), implication_number_of_con_votes(a, b), implication_sum_of_votes(a,
                                                                                                                  b), get_implication_votes(
        a, b)


def lerp(x, y, l):
    return x * l + y * (1 - l)


def lerp_colors(color_1, color_2, l):
    return lerp(color_1[0], color_2[0], l), lerp(color_1[1], color_2[1], l), lerp(color_1[2], color_2[2], l)


def implication_color(a, b):
    pro = implication_number_of_pro_votes(a, b)
    con = implication_number_of_con_votes(a, b)
    lerp_factor = pro / (pro + con) if (pro + con) > 0 else 0

    color_1 = COLOR_1
    color_2 = COLOR_2

    return lerp_colors(color_1, color_2, lerp_factor)


def search_list(term):
    with database.session() as db_session:
        if logged_in():
            o = db_session.run("CALL db.index.fulltext.queryNodes('text', \"" + term + "~\") YIELD node as opinion, score "
                               "OPTIONAL MATCH (:User) -[v:VOTED]-> (opinion)"
                               "OPTIONAL MATCH (u:User {username:$username}) -[u_v:VOTED]-> (opinion)"
                               "RETURN opinion, collect(v.vote) as votes, u_v.vote as own_vote "
                               "LIMIT 10",
                               username=current_user())
        else:
            o = db_session.run("CALL db.index.fulltext.queryNodes('text', \"" + term + "~\") YIELD node as opinion, score "
                                                                                       "OPTIONAL MATCH (:User) -[v:VOTED]-> (opinion)"
                                                                                       "RETURN opinion, collect(v.vote) as votes"
                                                                                       "LIMIT 10")
        better = [to_opinion_dict(x['opinion'], x['votes'], x['own_vote']) for x in o]

        return better


def votes(o):
    with database.session() as db_session:
        r = db_session.run("MATCH (:User) -[v:VOTED ]-> (:Opinion { oid: $oid})"
                           "RETURN v.vote as vote",
                           oid=o['oid'])
        return [x['vote'] for x in r]


def lazy_get(dict, key, default):
    if key in dict:
        return dict[key]
    else:
        return default(dict)


def likes(o):
    vs = lazy_get(o, 'votes', votes)
    return len([v for v in vs if v == 1])


def dislikes(o):
    vs = lazy_get(o, 'votes', votes)
    return len([v for v in vs if v == -1])


def popularity(o):
    vs = lazy_get(o, 'votes', votes)
    return sum(vs)


def front_page_opinions():
    with database.session() as db_session:
        if logged_in():
            r = db_session.run("MATCH (opinion : Opinion)"
                               "OPTIONAL MATCH (:User) -[v:VOTED]-> (opinion)"
                               "OPTIONAL MATCH (u:User {username:$username}) -[u_v:VOTED]-> (opinion)"
                               "RETURN opinion, collect(v.vote) as votes, u_v.vote as own_vote",
                               username=current_user())

            besser = [to_opinion_dict(x['opinion'], x['votes'], x['own_vote']) for x in r]
        else:
            r = db_session.run("MATCH (opinion : Opinion)"
                               "OPTIONAL MATCH (:User) -[v:VOTED]-> (opinion)"
                               "RETURN opinion, collect(v.vote) as votes")

            besser = [to_opinion_dict(x['opinion'], x['votes']) for x in r]

        besser.sort(key=popularity, reverse=True)
        return besser


app.jinja_env.globals.update(likes=likes)
app.jinja_env.globals.update(dislikes=dislikes)


def logged_in():
    if 'username' in session:
        return True
    else:
        return False


app.jinja_env.globals.update(logged_in=logged_in)


def current_user():
    return session.get('username', None)


app.jinja_env.globals.update(current_user=current_user)


def get_input_opinions(oid):
    with database.session() as db_session:
        if logged_in():
            input_result = db_session.run("MATCH (o : Opinion { oid : $oid})"
                                          "MATCH (a)-[:IMPLICATION]->(i:Implication)-[:IMPLICATION]->(o)"
                                          "OPTIONAL MATCH (:User) -[v:VOTED]-> (a)"
                                          "OPTIONAL MATCH (u:User {username:$username}) -[u_v:VOTED]-> (a)"
                                          "RETURN a as opinion, collect(v.vote) as votes, u_v.vote as own_vote",
                                          oid=oid, username=current_user())
        else:
            input_result = db_session.run("MATCH (o : Opinion { oid : $oid})"
                                          "MATCH (a)-[:IMPLICATION]->(i:Implication)-[:IMPLICATION]->(o)"
                                          "MATCH (:User) -[v:VOTED]-> (a)"
                                          "RETURN a as opinion, collect(v.vote) as votes",
                                          oid=oid)
        input_ugly = [to_opinion_dict(x['opinion'], x['votes'], x.get('own_vote')) for x in input_result]
        input_with_stats = [(x, implication_stats(x['oid'], oid), implication_color(x['oid'], oid)) for x in input_ugly]
        input_with_stats.sort(key=lambda t: sum([abs(x) for x in t[1][3]]) + sum([abs(x) for x in t[0]['votes']]),
                              reverse=True)
        return input_with_stats


def get_output_opinions(oid):
    with database.session() as db_session:
        if logged_in():
            output_result = db_session.run("MATCH (o : Opinion { oid : $oid})"
                                           "MATCH (o)-[:IMPLICATION]->(i:Implication)-[:IMPLICATION]->(a)"
                                           "OPTIONAL MATCH (:User) -[v:VOTED]-> (a)"
                                           "OPTIONAL MATCH (u:User {username:$username}) -[u_v:VOTED]-> (a)"
                                           "RETURN a as opinion, collect(v.vote) as votes, u_v.vote as own_vote",
                                           oid=oid, username=current_user())
        else:
            output_result = db_session.run("MATCH (o : Opinion { oid : $oid})"
                                           "MATCH (o)-[:IMPLICATION]->(i:Implication)-[:IMPLICATION]->(a)"
                                           "MATCH (:User) -[v:VOTED]-> (a)"
                                           "RETURN a as opinion, collect(v.vote) as votes",
                                           oid=oid, username=current_user())

        output = [to_opinion_dict(x['opinion'], x['votes'], x.get('own_vote') or 0) for x in output_result]
        output_with_stats = [(x, implication_stats(oid, x['oid'])) for x in output]
        output_with_stats.sort(key=lambda t: sum([abs(x) for x in t[1][3]]) + sum([abs(x) for x in t[0]['votes']]),
                               reverse=True)
        return output_with_stats


def get_opinion(oid, user=None):
    with database.session() as db_session:
        if user:
            o = db_session.run("MATCH (o : Opinion { oid : $oid})"
                               "OPTIONAL MATCH (:User) -[v:VOTED]-> (o)"
                               "OPTIONAL MATCH (u:User {username:$user}) -[u_v:VOTED]-> (o)"
                               "RETURN o, collect(v.vote) as votes, u_v.vote as own_vote",
                               oid=oid, user=user)
            s = o.single()
            return to_opinion_dict(s['o'], s['votes'], s['own_vote'])

        else:
            o = db_session.run("MATCH (o : Opinion { oid : $oid})"
                               "OPTIONAL MATCH (:User) -[v:VOTED]-> (o)"
                               "RETURN o, collect(v.vote) as votes",
                               oid=oid)
            s = o.single()
            return to_opinion_dict(s['o'], s['votes'])


def to_opinion_dict(x, votes, own_vote=0):
    return {'text': x['text'], 'oid': x['oid'], 'votes': votes, 'own_vote': own_vote or 0}


def render_opinion(oid):
    return render_template('home.html', current_oid=oid, opinion=get_opinion(oid, current_user()),
                           input_opinions=get_input_opinions(oid),
                           output_opinions=get_output_opinions(oid))


@app.route('/', methods=['GET'])
def home():
    searchword = request.args.get('search', None)
    if searchword:
        return render_template("search.html", result=search_list(searchword))
    else:
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


@app.route('/search/<term>')
def summary(term):
    d = search_list(term)
    print(d)
    return jsonify(d)


@app.route('/connect/', methods=['POST'])
def connect():
    from_id = int(request.form['from'])
    to_id = int(request.form['to'])
    vote = request.form['vote']
    if vote == "1":
        vote = 1
    else:
        vote = -1

    if from_id != to_id and logged_in():
        add_implication(from_id, to_id, current_user())
        vote_implication(from_id, to_id, current_user(), vote)
    return "suckcess"


@app.route('/vote_opinion/', methods=['POST'])
def vote_opinion_handler():
    oid = int(request.form['oid'])
    vote = int(request.form['vote'])
    if logged_in():
        vote_opinion(oid, vote, current_user())
        return "suckcess"
    else:
        return "not logged in, bitch"


@app.route('/vote_implication/', methods=['POST'])
def vote_implication_handler():
    from_id = int(request.form['from'])
    to_id = int(request.form['to'])
    vote = int(request.form['vote'])
    if logged_in():
        vote_implication(from_id, to_id, current_user(), vote)
    return "suckcess"


# Set the secret key to some random bytes. Keep this really secret!
app.secret_key = b'yu8Qy4xkBdCvMSJQiZG8k3Vbdv4GUf'


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
                add_user(u, p)
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
