from collections import defaultdict

from surprise import Reader, SVD, Dataset
import pandas as pd
import pickle
import os.path
from multiprocessing.connection import Listener
from threading import Thread
import sys
import atexit

from surprise.model_selection import train_test_split


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
    ratings_dict = {'itemID': [1, 1, 1, 2, 2],
                    'userID': [9, 32, 2, 45, 'user_foo'],
                    'rating': [3, 2, 1, 3, 1]}
user_dict = load_obj("users")
if not user_dict:
    user_dict = {}

picture_dict = load_obj("pictures")
if not picture_dict:
    picture_dict = {"n":0}

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
    #return [algo.predict(userID,iid) for iid in trainset.all_items()]
    return [algo.estimate(iuid, iiid) for iiid in trainset.all_items()]


def get_top_n_from_predictions(predictions, n=10):
    """Return the top-N recommendation for each user from a set of predictions.

    Args:
        predictions(list of Prediction objects): The list of predictions, as
            returned by the test method of an algorithm.
        n(int): The number of recommendation to output for each user. Default
            is 10.

    Returns:
    A dict where keys are user (raw) ids and values are lists of tuples:
        [(raw item id, rating estimation), ...] of size n.
    """

    # First map the predictions to each user.
    top_n = defaultdict(list)
    for uid, iid, true_r, est, _ in predictions:
        top_n[uid].append((iid, est))

    # Then sort the predictions for each user and retrieve the k highest ones.
    for uid, user_ratings in top_n.items():
        user_ratings.sort(key=lambda x: x[1], reverse=True)
        top_n[uid] = user_ratings[:n]

    return top_n


print(calculate_predictions('user_foo'))
print(calculate_predictions('faggot'))


def get_top_n(userID, n = 10):
    print(calculate_predictions(2))
    r = calculate_predictions(userID).sort(key=lambda x: x[1], reverse=True)
    return r[:n]
    #return get_top_n_from_predictions(calculate_predictions())[userID]

#add_rating(2, 3, 1)
#print(get_top_n(2))


# save_obj(ratings_dict,"ratings")

def handle_msg(msg, conn):
    if msg == "add_user":
        salt = bcrypt.gensalt(12)
        password = msg["password"]
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        user_dict[msg["username"]] = hashed_password
    elif msg == "get_user":
        conn.send(user_dict[msg["username"]])
    elif msg == "send_rating":
        add_rating(msg["item"], msg["username"], msg["rating"])
    elif msg == "get_top_n":
        conn.send(get_top_n(msg["username"]))
    elif msg == "get_pic":
        conn.send(picture_dict[msg["item"]])
    elif msg == "send_pic":
        picture_dict[picture_dict["n"]] = msg["filename"]
        picture_dict["n"] +=1
    pass

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
    save_obj(ratings_dict,"ratings")
    save_obj(picture_dict, "pictures")
    listener.close()


atexit.register(exit_handler)


while True:
    conn = listener.accept()
    print('connection accepted from', listener.last_accepted)
    thread = Thread( target= on_new_client, args= (conn, ))
    thread.start()

