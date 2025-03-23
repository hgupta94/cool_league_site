import time
from functools import wraps


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