from scripts.utils import constants as const
import mysql.connector


def flatten_list(lst: list) -> list:
    """Flattens a list of lists into a single list"""
    return [
        x
        for xs in lst
        for x in xs
    ]


def mysql_connection() -> mysql.connector:
    """Creates a MySQL connection obejct"""

    conn = mysql.connector.connect(
        host=const.DB_HOST,
        user=const.USERNAME,
        password=const.DB_PASS,
        database=const.DB
    )

    return conn
