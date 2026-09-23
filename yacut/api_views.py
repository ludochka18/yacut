from http import HTTPStatus

from flask import jsonify, request

from . import app
from .error_handlers import InvalidAPIUsage
from .models import URLMap


@app.route('/api/id/', methods=['POST'])
def create_short_link():
    data = request.get_json(silent=True)
    if data is None:
        raise InvalidAPIUsage('Отсутствует тело запроса')
    if not isinstance(data, dict):
        raise InvalidAPIUsage('Тело запроса должно быть JSON-объектом')
    if 'url' not in data:
        raise InvalidAPIUsage('"url" является обязательным полем!')
    try:
        item = URLMap.create(data['url'], data.get('custom_id'))
    except ValueError as error:
        raise InvalidAPIUsage(str(error)) from error
    return jsonify(item.to_dict()), HTTPStatus.CREATED


@app.route('/api/id/<string:short_id>/', methods=['GET'])
def get_original_link(short_id):
    item = URLMap.get(short_id)
    if item is None:
        raise InvalidAPIUsage('Указанный id не найден', HTTPStatus.NOT_FOUND)
    return jsonify(url=item.original)
