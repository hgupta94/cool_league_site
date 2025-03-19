from scripts.utils import (utils,
                           constants)
import mysql.connector
import pandas as pd


def mysql_connection() -> mysql.connector:
    """Creates a MySQL connection object"""

    conn = mysql.connector.connect(
        host=constants.DB_HOST,
        user=constants.USERNAME,
        password=constants.DB_PASS,
        database=constants.DB
    )

    return conn

def sql_insert_query(table: str,
                     columns: str) -> str:
    """Generates a SQL INSERT query for the specified table"""

    query = f'''
            INSERT INTO
            {table}
                {columns}
            VALUES
                {('%s',) * len(columns.split(', '))};
            '''
    return query


def commit_row(connection,
               table: str,
               columns: str,
               values: tuple) -> None:
    """Commits a row to the specified table"""

    c = connection.cursor()
    query = sql_insert_query(table=table, columns=columns)
    c.execute(query, values)
    connection.commit()


def commit_data(data: dict|list|pd.DataFrame,
                table: str,
                columns: str,
                values: tuple) -> None:
    """Commits data to the database"""

    with mysql_connection() as conn:
        if isinstance(data, dict):
            for _, _ in data.items():
                commit_row(connection=conn,
                           table=table,
                           columns=columns,
                           values=values)

        if isinstance(data, list):
            for _ in data:
                commit_row(connection=conn,
                           table=table,
                           columns=columns,
                           values=values)

        if isinstance(data, pd.DataFrame):
            for _, _ in data.iterrows():
                commit_row(connection=conn,
                           table=table,
                           columns=columns,
                           values=values)