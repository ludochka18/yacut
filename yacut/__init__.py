import click
from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from settings import Config

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

from . import api_views, error_handlers, models, views  # noqa: E402, F401


@app.cli.command('init-db')
def init_db_command():
    """Create database tables for a fresh local installation."""
    db.create_all()
    click.echo('База данных создана.')
