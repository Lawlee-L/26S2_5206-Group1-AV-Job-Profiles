from contextlib import contextmanager

import mysql.connector
from flask import current_app


@contextmanager
def database_connection():
    """Open and always close one MySQL connection."""
    connection = mysql.connector.connect(
        host=current_app.config["DB_HOST"],
        port=current_app.config["DB_PORT"],
        database=current_app.config["DB_NAME"],
        user=current_app.config["DB_USER"],
        password=current_app.config["DB_PASSWORD"],
        connection_timeout=current_app.config["DB_CONNECT_TIMEOUT"],
    )
    try:
        yield connection
    finally:
        connection.close()


def fetch_all(sql, params=()):
    with database_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()


def fetch_one(sql, params=()):
    with database_connection() as connection:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(sql, params)
            return cursor.fetchone()
        finally:
            cursor.close()


def ping_database():
    with database_connection() as connection:
        connection.ping(reconnect=False, attempts=1, delay=0)
