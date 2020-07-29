import atexit
import os.path
import pickle
from multiprocessing.connection import Listener
from threading import Thread

import bcrypt
import pandas as pd
from surprise import Reader, SVD, Dataset


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
    ratings_dict = {'itemID': [],
                    'userID': [],
                    'rating': []}

    # ratings_dict = {'itemID': [1, 1, 1, 2, 2],
    #                'userID': [9, 32, 2, 45, 'user_foo'],
    #                'rating': [3, 2, 1, 3, 1]}
user_dict = load_obj("users")
if not user_dict:
    user_dict = {}

picture_dict = load_obj("pictures")
if not picture_dict:
    picture_dict = {"n": 0, "unknown_pictures": {}, "pictures": {}}

print(ratings_dict)
print(user_dict)
print(picture_dict)


def add_rating(itemID, userID, rating):
    ratings_dict['itemID'] += [itemID]
    ratings_dict['userID'] += [userID]
    ratings_dict['rating'] += [rating]


def calculate_predictions(userID):
    df = pd.DataFrame(data=ratings_dict)
    reader = Reader(rating_scale=(1, 3))
    data = Dataset.load_from_df(df[['userID', 'itemID', 'rating']], reader)
    trainset = data.build_full_trainset()
    algo = SVD()
    algo.fit(trainset)
    iuid = trainset.to_inner_uid(userID)
    # return [algo.predict(userID,iid) for iid in trainset.all_items()]
    print("Halloo hier", picture_dict, trainset.all_items())
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
    # print(calculate_predictions(2))
    # print(calculate_predictions(2))
    try:
        r = calculate_predictions(username)
        print(r)
    except ValueError:
        print("Vaöuie")
        return random_memes(n)
    r.sort(key=lambda x: x[1], reverse=True)
    r = [item for (item, _) in r] + pick_n_unknown_memes(n)
    r = [item for item in r if item not in user_dict[username]["memes_rated"]]
    print("r", r)
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
    result = [0,0,0]
    for i in range(len(ratings_dict["itemID"])):
        if ratings_dict["itemID"][i] == itemID:
            result[ratings_dict["rating"][i]-1] += 1
    return result


# save_obj(ratings_dict,"ratings")

def handle_msg(msg, conn):
    print("buuts", msg)
    m = msg["msg"]
    if m == "add_user":
        if "username" in msg and "password" in msg and msg["username"] not in user_dict:
            salt = bcrypt.gensalt(12)
            password = msg["password"]
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
            user_dict[msg["username"]] = {"hashed_password": hashed_password, "memes_rated": {}}
    elif m == "get_user":
        if "username" in msg and msg["username"] in user_dict:
            conn.send(user_dict[msg["username"]])
        else:
            conn.send(None)
    elif m == "send_rating":
        if "username" in msg and "item" in msg and "rating" in msg:
            user_has_rated(msg["username"], msg["item"])
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
        if "filename" in msg and "username" in msg:
            itemID = picture_dict["n"]
            picture_dict["pictures"][itemID] = {"filename": msg["filename"], "username": msg["username"]}
            picture_dict["unknown_pictures"][itemID] = True
            picture_dict["n"] += 1
    elif m == "get_upload_overview":
        if "username" in msg:
            conn.send([(itemID, pic["filename"], total_rating(itemID)) for itemID, pic in picture_dict["pictures"].items() if
                       pic["username"] == msg["username"]])
        else:
            conn.send(None)


def on_new_client(conn):
    while True:
        try:
            msg = conn.recv()
            print("recieved " + str(msg))
            # sys.stdout.flush()
            # do something with msg
            if msg == 'close':
                conn.close()
                break

            handle_msg(msg, conn)
        except EOFError:
            print("lost connection")
            conn.close()
            break


address = ('localhost', 6000)  # family is deduced to be 'AF_INET'
listener = Listener(address, authkey=b'secret password')


def exit_handler():
    print("saving shit")
    save_obj(ratings_dict, "ratings")
    save_obj(picture_dict, "pictures")
    save_obj(user_dict, "users")
    listener.close()


atexit.register(exit_handler)

while True:
    conn = listener.accept()
    print('connection accepted from', listener.last_accepted)
    thread = Thread(target=on_new_client, args=(conn,))
    thread.start()
