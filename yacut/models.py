import re
import secrets
from datetime import datetime
from urllib.parse import urlsplit

from flask import url_for
from sqlalchemy.exc import IntegrityError

from . import db
from .constants import (
    ALPHABET, DUPLICATE_MESSAGE, INVALID_SHORT_MESSAGE,
    MAX_GENERATION_ATTEMPTS, MAX_SHORT_LENGTH,
    MAX_URL_LENGTH, RESERVED_IDS, SHORT_ID_LENGTH,
)


def validate_original(original):
    if not isinstance(original, str) or not original:
        raise ValueError('"url" является обязательным полем!')
    try:
        parsed = urlsplit(original)
        valid = parsed.scheme in ('http', 'https') and parsed.hostname
    except ValueError:
        valid = False
    if (not valid or len(original) > MAX_URL_LENGTH
            or any(char.isspace() for char in original)):
        raise ValueError('Указана некорректная ссылка')


def get_unique_short_id(length=SHORT_ID_LENGTH):
    """Generate an unused identifier of the requested length."""
    if not 1 <= length <= MAX_SHORT_LENGTH:
        raise ValueError('Недопустимая длина идентификатора')
    for _ in range(MAX_GENERATION_ATTEMPTS):
        short = ''.join(secrets.choice(ALPHABET) for _ in range(length))
        if short not in RESERVED_IDS and URLMap.get(short) is None:
            return short
    raise RuntimeError(
        'Не удалось сгенерировать уникальную короткую ссылку.'
    )


class URLMap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original = db.Column(db.Text, nullable=False)
    short = db.Column(db.String(MAX_SHORT_LENGTH), unique=True, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @staticmethod
    def get(short):
        return URLMap.query.filter_by(short=short).first()

    @property
    def short_link(self):
        return url_for('redirect_view', short_id=self.short, _external=True)

    def to_dict(self):
        return {'url': self.original, 'short_link': self.short_link}

    @classmethod
    def create(cls, original, custom_id=None):
        validate_original(original)
        if custom_id is not None and custom_id != '':
            if (not isinstance(custom_id, str)
                    or not re.fullmatch(r'[A-Za-z0-9]{1,16}', custom_id)):
                raise ValueError(INVALID_SHORT_MESSAGE)
            if custom_id in RESERVED_IDS or cls.get(custom_id):
                raise ValueError(DUPLICATE_MESSAGE)
        item = cls(original=original,
                   short=custom_id or get_unique_short_id())
        db.session.add(item)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise ValueError(DUPLICATE_MESSAGE) from None
        return item
