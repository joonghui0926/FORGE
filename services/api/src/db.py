import os
from contextlib import contextmanager

import psycopg

DATABASE_URL = os.environ["DATABASE_URL"]


@contextmanager
def get_conn():
    with psycopg.connect(DATABASE_URL) as conn:
        yield conn
