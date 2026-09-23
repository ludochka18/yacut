from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, MultipleFileField
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Regexp, URL

from .constants import MAX_SHORT_LENGTH, MAX_URL_LENGTH


class URLForm(FlaskForm):
    original_link = StringField('Длинная ссылка', validators=[
        DataRequired(message='Введите ссылку.'),
        Length(max=MAX_URL_LENGTH),
        URL(message='Введите корректную ссылку с http:// или https://.'),
    ])
    custom_id = StringField('Ваш вариант короткой ссылки', validators=[
        Optional(), Length(max=MAX_SHORT_LENGTH),
        Regexp(r'^[A-Za-z0-9]+$', message='Только латинские буквы и цифры.'),
    ])
    submit = SubmitField('Создать')


class FilesForm(FlaskForm):
    files = MultipleFileField('Выберите файлы', validators=[
        FileRequired(message='Выберите хотя бы один файл.'),
    ])
