import datetime
from argparse import ArgumentParser

import numpy
import pandas
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.externals import joblib
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.tree import DecisionTreeClassifier

from api import JirApi
from constants import HEADER


def main(update_type, update_model_flag, start_issue, end_issue):
    # TODO programatically generate model filename based on type
    model_name = 'test.pkl'

    data_frame = fetch_data(update_type, start_issue, end_issue)

    if update_model_flag:
        model = update_or_create_model(data_frame)
    else:
        model = joblib.load(model_name)


def update_or_create_model(data_frame):
    """
    Updates or creates model based upon data in dataframe.
    :param data_frame: pandas dataframe object
    :return: returns model
    """
    # TODO currently only creates; need to implement model updates
    training_set = create_training_subset(data_frame)

    x_vals = training_set.drop(['time_spent', 'key'], axis=1)
    y_vals = training_set['time_spent']

    x_train, x_test, y_train, y_test = train_test_split(x_vals, y_vals, test_size=0.3, random_state=100)

    classifier_gini = DecisionTreeClassifier(
        criterion='gini',
        random_state=100,
        max_depth=3,
        min_samples_leaf=5,
    )
    # print(numpy.unique(list(map(len, x_train))))
    print(data_frame)
    print(data_frame.shape)
    classifier_gini.fit(x_train, y_train)

    test_result = classifier_gini.predict(x_test)
    print(accuracy_score(y_test, test_result))

    return classifier_gini


def fetch_data(update_type, start_issue, end_issue):
    """
    Gets data from file, JIRA API or both depending on update_type
    :param update_type: val of "all" recreates dataset from scratch, "append" not yet implemented
    :param start_issue: starting ticket number to pull from
    :param end_issue: end ticket number to pull from
    :return: returns pandas data frame
    """
    try:
        # TODO: validate header from archive is same as above
        data_frame = pandas.DataFrame.from_csv('issues.csv')
    except FileNotFoundError:
        if not update_type:
            raise
        data_frame = pandas.DataFrame(columns=HEADER)

    if update_type == 'all':
        print("Updating all issue data")
        jira = JirApi(start_issue=start_issue, end_issue=end_issue)
        data_frame = jira.collect_issues(data_frame)
        data_frame.to_csv('issues.csv')
    elif update_type == 'append':
        # TODO: Programatically determine start_ & end_issue vals
        raise Exception('Append new data not implemented. Use -U to update entire dataset.')

    data_frame = convert_datetimes_to_ordinals(data_frame)
    data_frame = vectorize_text_fields(data_frame)

    return data_frame


def create_training_subset(data_frame):
    """
    Strips out all rows that do not have an actual time spent value.
    :param data_frame: pandas data frame
    :return: training set data frame
    """
    training_set = data_frame.loc[data_frame['time_spent'].notnull()]
    return training_set


def vectorize_text_fields(data_frame):
    """
    Creates a tfidf vector for all columns of dtype numpy.object
    :param data_frame: pandas data frame
    :return: pandas data frame
    """
    vectorizer = TfidfVectorizer()
    excluded_columns = ['time_spent', 'key', 'original_estimate', 'remaining_estimate']
    for column_name in data_frame:
        if column_name not in excluded_columns and data_frame[column_name].dtype == numpy.object:
            tfidf_vect = vectorizer.fit_transform(data_frame[column_name].values.astype('U'))
            vect_df = list(tfidf_vect.toarray())
            # data_frame = pandas.concat([data_frame, vect_df])
            data_frame[column_name] = vect_df

    return data_frame


def convert_datetimes_to_ordinals(data_frame):
    """
    Converts datetime columns in data frame to ordinals
    :param data_frame: pandas data frame
    :return: pandas data frame
    """
    date_columns = ['created_datetime', 'updated_datetime', 'resolved_datetime']
    for column in date_columns:
        data_frame[column] = pandas.to_datetime(data_frame[column])
        data_frame[column] = data_frame[column].map(datetime.datetime.toordinal)

    return data_frame


if __name__ == '__main__':
    parser = ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-u",
        "--update-issues",
        dest="update_issues",
        help="Update issue data set",
        action="store_true",
    )
    group.add_argument(
        "-U",
        "--update-all-issues",
        dest="update_all_issues",
        help="Recreate issue data set",
        action="store_true",
    )
    parser.add_argument(
        "-s",
        "--start-issue",
        type=int,
        dest="start_issue",
        help="First issue to pull",
    )
    parser.add_argument(
        "-e",
        "--end-issue",
        type=int,
        dest="end_issue",
        help="Last issue to pull",
    )
    parser.add_argument(
        "-m",
        "--update-model",
        dest="update_model",
        help="Update model flag",
        action="store_true",
    )
    args = parser.parse_args()
    update_issues_flag = args.update_issues
    update_all_issues = args.update_all_issues
    update_model_flag = args.update_model
    start_issue = args.start_issue
    end_issue = args.end_issue

    if update_all_issues:
        update_type = 'all'
    elif update_issues_flag:
        update_type = 'append'
    else:
        update_type = None

    main(update_type, update_model_flag, start_issue, end_issue)
