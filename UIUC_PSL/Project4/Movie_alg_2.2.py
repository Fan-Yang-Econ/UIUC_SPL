from surprise import SVD
from surprise.model_selection import cross_validate
from surprise import NormalPredictor
from surprise import Dataset
from surprise import Reader
import pandas as pd
import os
from surprise import KNNBasic, KNNWithZScore, KNNWithMeans, accuracy
from surprise.model_selection import KFold, GridSearchCV
import numpy as np
from surprise import similarities

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
pd.set_option('display.max_colwidth', 40)

# load data
FOLDER = '/Users/fanyang/Dropbox/uiuc/cs598/UIUC_SPL/UIUC_PSL/Project4/'
df_movie = pd.read_csv(os.path.join(FOLDER, 'movies.csv'))
df_rating = pd.read_csv(os.path.join(FOLDER, 'ratings.csv'))
## 6040 users
df_users =  pd.read_csv(os.path.join(FOLDER, 'users.csv'))


# use Surprise
reader = Reader(rating_scale=(1, 5))
rating_data = Dataset.load_from_df(df_rating[['UserID', 'MovieID', 'Rating']], reader)
anti_set = rating_data.build_full_trainset().build_anti_testset()


# 10 iterations
fold = 10
kf = KFold(n_splits=fold)

i = 1
for trainset, testset in kf.split(rating_data):
    # use first fold to do parameter tuning
    if i<=1:
        param_grid = {'k': [10, 50, 100],
                      'sim_options': {'name': ['cosine'],
                                      'user_based': [False]}
                      }
        gs = GridSearchCV(KNNWithMeans, param_grid, measures=['rmse'], cv=3)
        gs.fit(rating_data)
        i += 1

df_cv = pd.DataFrame.from_dict(gs.cv_results)


best_k = gs.best_params['rmse']['k']
sim_options = {'name': 'cosine',
               'user_based': False # compute  similarities between items
               }

algo = KNNWithMeans(k = best_k, sim_options = sim_options)

accuracy_list = []
for trainset, testset in kf.split(rating_data):

        # train and test algorithm.
        algo.fit(trainset)
        predictions = algo.test(testset)
        # Compute and print Root Mean Squared Error
        current_acc = accuracy.rmse(predictions, verbose=True)
        accuracy_list.append(current_acc)

# pred_df_test = pd.DataFrame(predictions).merge(df_rating , left_on = ['uid', 'iid'], right_on = ['UserID', 'MovieID'])

# anti_pre = algo.test(anti_set)
# merge prediction with pandas
# pred_df = pd.DataFrame(anti_pre).merge(df_movie , left_on = ['iid'], right_on = ['MovieID'])
# pred_df = pd.DataFrame(pred_df).merge(df_users , left_on = ['uid'], right_on = ['UserID'])


import timeit
start = timeit.default_timer()
# new user rating data
rating_movie = [2905, 2019, 858, 1198, 260]
rating_result = [1, 1, 1, 1, 1]
n = len(rating_result)
user_list = [0]* n

ratings_dict = {'UserID': user_list,
                'MovieID': rating_movie,
                'Rating': rating_result}
df_new= pd.DataFrame(ratings_dict)

# add new user data to existing data, for quick processing, only use 30% of the data
original_data = df_rating[['UserID', 'MovieID', 'Rating']]\
    # .sample(frac = 0.3)
df_new_rating = df_new.append(original_data[['UserID', 'MovieID', 'Rating']], ignore_index=True)
reader = Reader(rating_scale=(1, 5))
new_data = Dataset.load_from_df(df_new_rating[['UserID', 'MovieID', 'Rating']], reader)
new_train = new_data.build_full_trainset()
# run algo
algo = KNNWithMeans(k = best_k, sim_options = sim_options)
algo.fit(new_train)
# prediction
movie_list = [movie for movie in original_data['MovieID'].unique().tolist() if movie not in rating_movie]
uid = 0
pred_list = []
for movie in movie_list:
    iid = movie
    pred = algo.predict(uid, iid)[3]
    pred_list.append(pred)

top_5_idx = np.argsort(pred_list)[-5:]
top_5_pred_value = [pred_list[i] for i in top_5_idx]
top5_movie_id = [movie_list[i] for i in top_5_idx]

df_movie[df_movie['MovieID'].isin(top5_movie_id)]
df_movie[df_movie['MovieID'].isin(rating_movie)]
stop = timeit.default_timer()
print('Time: ', stop - start)

#       MovieID                                    Title       Genres  Year
# 977       989  Schlafes Bruder (Brother of Sleep) (...        Drama  1995
# 1762     1830                  Follow the Bitch (1998)       Comedy  1998
# 3211     3280                         Baby, The (1973)       Horror  1973
# 3313     3382                   Song of Freedom (1936)        Drama  1936
# 3811     3881                 Bittersweet Motel (2000)  Documentary  2000



# find K-nearest neighbors
dic_50NN = {}
movieID_list = df_rating['MovieID'].unique().tolist()
# best_k =50
full_train = rating_data.build_full_trainset()
algo = KNNWithMeans(k = best_k, sim_options = sim_options)
algo.fit(full_train)

noNN_movie_list = []
for movie in movieID_list:
    movie_inner_iid = full_train.to_inner_iid(movie)
    if trainset.knows_item(movie_inner_iid):
        # input output both are inner iid
        k_nn = algo.get_neighbors(movie_inner_iid, k=best_k)
        dic_50NN[movie_inner_iid] = k_nn
    else:
        # dic_50NN[movie] = []
        noNN_movie_list.append(movie_inner_iid)

dic_i_in_j_NN = {}
for i in dic_50NN.keys():
    for j, movie_list in dic_50NN.items():
        if i in movie_list:
            if i not in dic_i_in_j_NN:
                dic_i_in_j_NN[i] = [j]
            else:
                dic_i_in_j_NN[i].append(j)
# test_list = []
# for j_list in dic_i_in_j_NN.values():
#     test_list.append(len(j_list))

# test1 = list(dic_i_in_j_NN.keys())
# test2 = list(dic_50NN.keys())
# [i for i in test2 if i not in test1]
algo.compute_similarities()
sim_matrix = algo.sim
# matrix index should be inner iid
record_list = []
for i in dic_i_in_j_NN.keys():
    i_raw_id = full_train.to_raw_iid(i)
    for j in dic_i_in_j_NN[i]:
        sim = sim_matrix[i,j]
        j_raw_id = full_train.to_raw_iid(j)
        record = {'MovieID': i_raw_id,
                  'Whose_NN': j_raw_id,
                  'similarity': sim}
        record_list.append(record)
# pd.DataFrame.from_dict(final_result)
# avg rating for each movie


avg_rating = df_rating.groupby('MovieID')['Rating'].mean()
# std_rating = df_rating.groupby('MovieID')['Rating'].std()

rating_movie = [2905, 2019, 858, 1198, 260]
rating_result = [1, 1, 1, 1, 1]
# n = len(rating_result)
# not impacted movie
movieID_list = df_rating['MovieID'].unique().tolist()
pred_list = []
for movie in movieID_list:
    movie_inner_iid = full_train.to_inner_iid(movie)
    if not bool(set(dic_50NN[movie_inner_iid]) & set(rating_movie)):
        pred_rating = avg_rating.loc[movie]
        pred_record = {'MovieID' : movie,
                       'pred': pred_rating}
        pred_list.append(pred_record)
    else:





