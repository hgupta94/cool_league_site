import os
from scripts.utils import constants
import mysql.connector
import pandas as pd
from sshtunnel import SSHTunnelForwarder


class Database:
    def __init__(
            self,
            use_ssh: bool = True
    ) -> None:
        """
        Initializes a Database object

        Args:
            use_ssh (bool): use SSH tunnel to connect to the database remotely
        """
        self.use_ssh = use_ssh
        self.connection = None
        self.tunnel = None

    def __enter__(self):
        if self.use_ssh:
            self.tunnel = SSHTunnelForwarder(
                (constants.DB_HOST_SSH, 22),
                ssh_username=constants.DB_USER_SSH,
                ssh_password=os.getenv('PA_PASS'),
                remote_bind_address=(constants.DB_MYSQL_HOST_SSH, 3306)
            )
            self.tunnel.start()
            self.connection = mysql.connector.connect(
                host='127.0.0.1',
                port=self.tunnel.local_bind_port,
                user=constants.DB_USER_SSH,
                password=constants.DB_PASS_SSH,
                database=constants.DB_NAME_SSH
            )
        else:
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
        if self.tunnel:
            self.tunnel.stop()

    def retrieve_data(self, table: str, how: str, season: int = None, week: int = None):
        query = ''
        if how == 'week':
            query = f'''
                    SELECT *
                    FROM {table}
                    WHERE season = {season}
                        AND week = {week};
                    '''
        if how == 'season':
            query = f'''
                    SELECT *
                    FROM {table}
                    WHERE season = {season}
                        AND week <= {week};
                    '''
        if how == 'all':
            query = f'''
                    SELECT *
                    FROM {table};
                    '''
        with self as conn:
            return pd.read_sql(query, conn)

    @staticmethod
    def sql_insert_query(table: str, columns: str) -> str:
        """Generate the SQL INSERT query for the specified table"""
        query = f'''
                INSERT INTO
                {table}
                    ({columns})
                VALUES
                    ({', '.join(('%s',) * len(columns.split(', ')))});
                '''
        return query

    def sql_update_table(
            self,
            table: str,
            values: tuple,
            set_column: str,
            new_value: str | int | float,
            id_column: str,
            id_value: str,
            season: int,
            week: int
    ) -> str:
        """Generate a SQL query to update a specific value"""
        if type(id_value) == str:  # need to add quotes around value
            query = f"""
                UPDATE {table}
                SET {set_column} = {new_value}
                WHERE {id_column} = '{id_value}' AND season = {season} and week = {week}
            """
        else:
            query = f"""
                UPDATE {table}
                SET {set_column} = {new_value}
                WHERE {id_column} = {id_value} AND season = {season} and week = {week}
            """
        with self as db:
            c = db.cursor()
            c.execute(query, values)
            db.commit()

    def commit_row(
            self,
            table: str,
            columns: str,
            values: tuple
    ) -> None:
        """Commit a row to the specified table"""
        with self as db:
            c = db.cursor()
            query = self.sql_insert_query(table, columns)
            c.execute(query, values)
            db.commit()

    def commit_data(
            self, table:
            str, columns:
            str, values:
            tuple, data:
            dict|list|pd.DataFrame
    ) -> None:
        """Commit data to the database"""
        with self:
            if isinstance(data, dict):
                for _, _ in data.items():
                    self.commit_row(table, columns, values)

            if isinstance(data, list):
                for _ in data:
                    self.commit_row(table, columns, values)

            if isinstance(data, pd.DataFrame):
                for _, _ in data.iterrows():
                    self.commit_row(table, columns, values)

    def batch_insert(
            self,
            table: str,
            columns: str,
            rows: list[tuple],
            chunk_size: int = 1000,
            upsert: bool = False,
            update_columns: list[str] | None = None,
    ) -> int:
        """
        Batch insert rows into a table

        Args:
            rows (list[tuple]): ordered row tuples matching columns order
            table (str): name of the target table
            columns (str): comma-separated column names
            chunk_size (int): number of rows per executemany call
            upsert (bool): if True, use ON DUPLICATE KEY UPDATE
            update_columns (list[str] | None): columns to update on duplicate key
                defaults to all columns except common id fields
        Returns:
            int: number of rows inserted
        """
        if not rows:
            print('0 rows committed')
            return None

        cols = [c.strip() for c in columns.split(',')]
        n_cols = len(cols)

        # ensure row widths match columns
        for i, row in enumerate(rows):
            if len(row) != n_cols:
                raise ValueError(
                    f'Row {i} has {len(row)} values but expected {n_cols} for columns {cols}'
                )

        placeholders = ', '.join(['%s'] * n_cols)
        col_sql = ', '.join(cols)
        sql = f'INSERT INTO {table} ({col_sql}) VALUES ({placeholders})'

        if upsert:
            if update_columns is None:
                skip = {'id', 'season', 'week'}
                update_columns = [c for c in cols if c not in skip]
            if not update_columns:
                raise ValueError('No columns available to update for upsert=True')
            update_sql = ', '.join([f'{c}=VALUES({c})' for c in update_columns])
            sql = f'{sql} ON DUPLICATE KEY UPDATE {update_sql}'
            print_str = '{} rows updated in {}'

        total = 0
        with self as conn:
            cur = conn.cursor()
            try:
                for i in range(0, len(rows), chunk_size):
                    batch = rows[i:i + chunk_size]
                    cur.executemany(sql, batch)
                    total += len(batch)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()

        print_str = '{} rows inserted in {}'
        print(print_str.format(total, table))
        return None
