import os
import secrets

from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///db.sqlite3')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY') or secrets.token_hex(32)
    DISK_TOKEN = os.getenv('DISK_TOKEN', '')
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024
