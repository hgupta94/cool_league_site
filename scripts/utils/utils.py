import time
from functools import wraps
import pandas as pd


def flask_get_columns(data: pd.DataFrame) -> tuple[list[str]]:
    """
    Return columns for Flask front end table
    """
    return tuple(data.columns)


def flask_get_data(data) -> list[tuple]:
    """
    Return data formated for Flask front end table
    """
    if type(data) == pd.DataFrame:
        return [tuple(x) for x in data.to_numpy()]

    if type(data) == list:
        return [tuple(x) for x in data]


def flatten_list(lst: list) -> list:
    """
    Flattens a list of lists into a single list
    Only works for 2D lists
    """
    return [
        x
        for xs in lst
        for x in xs
    ]


def timer(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = function(*args, **kwargs)
        end = time.perf_counter()
        print(f'Executed in {end - start} seconds')
        return result
    return wrapper