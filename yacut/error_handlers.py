from http import HTTPStatus

from flask import jsonify, render_template, request
from flask_wtf.csrf import CSRFError

from . import app, db


class InvalidAPIUsage(Exception):
    def __init__(self, message, status_code=HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@app.errorhandler(InvalidAPIUsage)
def invalid_api_usage(error):
    return jsonify(message=error.message), error.status_code


def error_response(code, message):
    if request.path.startswith('/api/'):
        return jsonify(message=message), code
    return render_template('error.html', code=code, message=message), code


@app.errorhandler(404)
def not_found(error):
    return error_response(404, 'Страница не найдена')


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return error_response(500, 'Внутренняя ошибка сервера')


@app.errorhandler(413)
def too_large(error):
    return error_response(413, 'Общий размер файлов превышает 32 МБ')


@app.errorhandler(405)
def method_not_allowed(error):
    return error_response(405, 'Метод не поддерживается')


@app.errorhandler(CSRFError)
def csrf_error(error):
    return error_response(400, 'Обновите страницу и отправьте форму ещё раз')
