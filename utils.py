import os
from dotenv import load_dotenv

def load_env():
    load_dotenv()

def get_db_path(filename):
    return os.path.join(os.getcwd(), filename)
