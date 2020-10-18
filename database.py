import atexit
import json
import os.path
import pickle
import signal
from multiprocessing.connection import Listener
from threading import Thread

import bcrypt
import pandas as pd
from surprise import Reader, SVD, Dataset

from util import load_config


def save_obj(obj, name):
    with open(name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


def load_obj(name):
    if os.path.isfile(name + '.pkl'):
        with open(name + '.pkl', 'rb') as f:
            return pickle.load(f)
    else:
        return None


ratings_dict = load_obj("ratings")
if not ratings_dict:
    ratings_dict = {}

user_dict = load_obj("users")
if not user_dict:
    user_dict = {}

picture_dict = load_obj("pictures")
if not picture_dict:
    picture_dict = {"n": 0, "unknown_pictures": {}, "pictures": {}}


def add_rating(itemID, userID, rating):
    user_has_rated(userID, itemID)
    ratings_dict[userID][itemID] = rating


def ratings_dict_to_table():
    t = {'itemID': [],
         'userID': [],
         'rating': []}

    for userID in ratings_dict:
        for itemID, rating in ratings_dict[userID].items():
            t['itemID'] += [itemID]
            t['userID'] += [userID]
            t['rating'] += [rating]

    return t


def calculate_predictions(userID):
    df = pd.DataFrame(data=ratings_dict_to_table())
    reader = Reader(rating_scale=(1, 3))
    data = Dataset.load_from_df(df[['userID', 'itemID', 'rating']], reader)
    trainset = data.build_full_trainset()
    algo = SVD()
    algo.fit(trainset)
    iuid = trainset.to_inner_uid(userID)
    # return [algo.predict(userID,iid) for iid in trainset.all_items()]
    return [(iiid, algo.estimate(iuid, iiid)) for iiid in trainset.all_items()]


def pick_n_from_dict(dict, n=10):
    result = []
    i = 0
    for key in dict:
        result += [key]
        i += 1
        if i >= n:
            break

    return result


def pick_n_unknown_memes(n=10):
    return pick_n_from_dict(picture_dict["unknown_pictures"], n)


def random_memes(n=10):
    return pick_n_from_dict(picture_dict["pictures"], n)


def get_top_n(username, n=10):
    try:
        r = calculate_predictions(username)
    except ValueError:
        return random_memes(n)
    r.sort(key=lambda x: x[1], reverse=True)
    r = [item for (item, _) in r] + pick_n_unknown_memes(n)
    r = [item for item in r if item not in user_dict[username]["memes_rated"]]
    if not r:
        return pick_n_unknown_memes(n)
    else:
        return r[:n]
    # return get_top_n_from_predictions(calculate_predictions())[userID]


# add_rating(2, 3, 1)
# print(get_top_n(2))


def user_has_rated(username, itemID):
    # print(user_dict)
    user_dict[username]["memes_rated"][itemID] = True
    if itemID in picture_dict["unknown_pictures"]:
        del picture_dict["unknown_pictures"][itemID]
    # print(user_dict)


def total_rating(itemID):
    result = [0, 0, 0]
    for userID in ratings_dict:
        for iid, rating in ratings_dict[userID].items():
            if iid == itemID:
                result[rating - 1] += 1
    return result


# save_obj(ratings_dict,"ratings")

def hash_password(password):
    salt = bcrypt.gensalt(12)
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password


def add_user(username, password, registered):
    if username not in user_dict:
        user_dict[username] = {"hashed_password": hash_password(password), "memes_rated": {}, "registered": registered}
        ratings_dict[username] = {}


def handle_msg(msg, conn):
    m = msg["msg"]
    if m == "add_user":
        if "username" in msg and "password" in msg and msg["username"] not in user_dict:
            if "registered" in msg:
                r = msg["registered"]
            else:
                r = False
            add_user(msg["username"], msg["password"], r)
    elif m == "merge_user":
        if "username" in msg and "password" in msg and msg["username"] not in user_dict and \
                "old_username" in msg and msg['old_username'] in user_dict:
            password = msg["password"]
            old_username = msg["old_username"]
            new_username = msg["username"]
            user_dict[new_username] = {"hashed_password": hash_password(password),
                                       "memes_rated": user_dict[old_username]["memes_rated"],
                                       "registered": True}
            ratings_dict[new_username] = ratings_dict[old_username]
            del ratings_dict[old_username]
            del user_dict[old_username]
            # for itemID, pic in picture_dict["pictures"].items():
            #    pic["username"] = new_username
    elif m == "get_user":
        if "username" in msg and msg["username"] in user_dict:
            conn.send(user_dict[msg["username"]])
        else:
            conn.send(None)
    elif m == "send_rating":
        if "username" in msg and "item" in msg and "rating" in msg:
            add_rating(msg["item"], msg["username"], msg["rating"])
    elif m == "get_top_n":
        if "username" in msg:
            conn.send(get_top_n(msg["username"]))
        else:
            conn.send(None)
    elif m == "get_pic":
        if "item" in msg and msg["item"] in picture_dict["pictures"]:
            conn.send(picture_dict["pictures"][int(msg["item"])])
        else:
            conn.send(None)
    elif m == "send_pic":
        if "filename" in msg and "username" in msg and "title" in msg and "show_username" in msg:
            itemID = picture_dict["n"]
            picture_dict["pictures"][itemID] = {"filename": msg["filename"], "username": msg["username"],
                                                "title": msg["title"], "show_username": msg["show_username"]}
            picture_dict["unknown_pictures"][itemID] = True
            picture_dict["n"] += 1
            add_rating(itemID, msg["username"], 2)

    elif m == "get_upload_overview":
        if "username" in msg:
            conn.send(
                [(itemID, pic["filename"], total_rating(itemID)) for itemID, pic in picture_dict["pictures"].items() if
                 pic["username"] == msg["username"]])
        else:
            conn.send(None)

    elif m == "save":
        save()


def on_new_client(conn):
    while True:
        try:
            msg = conn.recv()
            # sys.stdout.flush()
            # do something with msg
            if msg == 'close':
                conn.close()
                break

            handle_msg(msg, conn)
        except EOFError:
            conn.close()
            break


address = ('0.0.0.0', 6000)  # family is deduced to be 'AF_INET'
listener = Listener(address, authkey=load_config()["database"]["password"].encode())


def save():
    save_obj(ratings_dict, "ratings")
    save_obj(picture_dict, "pictures")
    save_obj(user_dict, "users")


def exit_handler():
    save()
    listener.close()


signal.signal(signal.SIGTERM, exit_handler)

atexit.register(exit_handler)

while True:
    conn = listener.accept()
    thread = Thread(target=on_new_client, args=(conn,))
    thread.start()
