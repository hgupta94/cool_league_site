from scripts.utils import constants
import mysql.connector
import pandas as pd


class Database:
    def __init__(self,
                 data: dict|list|pd.DataFrame = None,
                 table: str = None,
                 columns: str = None,
                 values: tuple = None,
                 season: int = None,
                 week: int = None):
        """
        Initializes a Database object

        Args:
            data: the data object to be committed
            table: name of the table in SQL
            columns: columns of the table in SQL
            values: table cell values to be commited
        """
        self.connection = None
        self.data = data
        self.table = table
        self.columns = columns
        self.values = values
        self.season = season
        self.week = week

    def __enter__(self):
        self.connection = mysql.connector.connect(
            host=constants.DB_HOST,
            user=constants.DB_USER,
            password=constants.DB_PASS,
            database=constants.DB_NAME
        )
        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        if self.connection:
            self.connection.close()

    def retrieve_data(self, how: str):
        if how == 'week':
            query = f'''
                    SELECT *
                    FROM {self.table}
                    WHERE season = {self.season}
                        AND week = {self.week};
                    '''
        if how == 'season':
            query = f'''
                    SELECT *
                    FROM {self.table}
                    WHERE season = {self.season}
                        AND week < {self.week};
                    '''
        if how == 'all':
            query = f'''
                    SELECT *
                    FROM {self.table};
                    '''
        with self as conn:
            return pd.read_sql(query, conn)

    def sql_insert_query(self) -> str:
        """Generate the SQL INSERT query for the specified table"""
        query = f'''
                INSERT INTO
                {self.table}
                    ({self.columns})
                VALUES
                    ({', '.join(('%s',) * len(self.columns.split(', ')))});
                '''
        return query

    def commit_row(self) -> None:
        """Commit a row to the specified table"""
        with self as db:
            c = db.cursor()
            query = self.sql_insert_query()
            c.execute(query, self.values)
            db.commit()

    def commit_data(self) -> None:
        """Commit data to the database"""
        with self.connection:
            if isinstance(self.data, dict):
                for _, _ in self.data.items():
                    self.commit_row()

            if isinstance(self.data, list):
                for _ in self.data:
                    self.commit_row()

            if isinstance(self.data, pd.DataFrame):
                for _, _ in self.data.iterrows():
                    self.commit_row()
