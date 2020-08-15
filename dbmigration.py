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


ratings_dict = load_obj("ratings")
new_ratings_dict = {}
if ratings_dict:
    for i in range(len(ratings_dict["itemID"])):
        itemID = ratings_dict["itemID"][i]
        userID = ratings_dict["userID"][i]
        rating = ratings_dict["rating"][i]

        if userID not in new_ratings_dict:
            new_ratings_dict[userID] = {}
        new_ratings_dict[userID][itemID] = rating

    save_obj(new_ratings_dict, "rating_migration")