import os
from app.services.db import connect


def list_users():
    # a comment
    return connect(os.getcwd())
