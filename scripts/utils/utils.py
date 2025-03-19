def flatten_list(lst: list) -> list:
    """Flattens a list of lists into a single list"""
    return [
        x
        for xs in lst
        for x in xs
    ]
