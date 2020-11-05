import os
import pickle



def save_obj(obj, name):
    with open(name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


def load_obj(name):
    if os.path.isfile(name + '.pkl'):
        with open(name + '.pkl', 'rb') as f:
            return pickle.load(f)
    else:
        return None


ratings = load_obj("ratings")
users = load_obj("users")
pictures = load_obj("pictures")

print(ratings)
print(users)
print(pictures)

it = list(ratings.items())
for username, rating in it:
    del ratings[username]
    ratings[username.lower()] = rating

it = list(users.items())
for username, user in it:
    del users[username]
    users[username.lower()] = user

for itemID, picture in pictures["pictures"].items():
    picture["username"] = picture["username"].lower()

save_obj(ratings, "ratings")
save_obj(users, "users")
save_obj(pictures, "pictures")

print(ratings)
print(users)
print(pictures)