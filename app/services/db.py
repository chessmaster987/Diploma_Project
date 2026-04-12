import os

import psycopg2
import psycopg2.extras


def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        host=os.getenv("DB_HOST"),
    )


def get_cursor(connection, dict_cursor=False):
    if dict_cursor:
        return connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
    return connection.cursor()
