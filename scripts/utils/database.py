from scripts.utils import constants
import mysql.connector
import pandas as pd


class Database:
    def __init__(self,
                 data: dict|list|pd.DataFrame = None,
                 table: str = None,
                 columns: str = None,
                 values: tuple = None):
        """
        Initializes a Database object

        Args:
            data: the data object to be committed
            table: name of the table in SQL
            columns: columns of the table in SQL
            values: table cell values to be commited
        """

        self.connection = mysql.connector.connect(
            host=constants.DB_HOST,
            user=constants.DB_USER,
            password=constants.DB_PASS,
            database=constants.DB_NAME
        )
        self.data = data
        self.table = table
        self.columns = columns
        self.values = values

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

        c = self.connection.cursor()
        query = self.sql_insert_query()
        c.execute(query, self.values)
        self.connection.commit()


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
