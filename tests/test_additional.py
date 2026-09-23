"""Regression checks for asynchronous uploads and validation."""
import asyncio
from io import BytesIO
from unittest.mock import AsyncMock

import pytest
from werkzeug.datastructures import FileStorage

from yacut import app, disk
from yacut.models import URLMap


@pytest.mark.parametrize('name', ['files', 'api', 'static'])
def test_reserved_names(client, name):
    response = client.post('/api/id/', json={
        'url': 'https://example.com', 'custom_id': name})
    assert response.status_code == 400
    assert URLMap.query.count() == 0


@pytest.mark.parametrize('url', [None, '', 1, [], 'javascript:alert(1)',
                                  'https://', 'https://example.com/a b'])
def test_invalid_original(client, url):
    assert client.post('/api/id/', json={'url': url}).status_code == 400
    assert URLMap.query.count() == 0


@pytest.mark.parametrize('value', [[], 1, False, {'x': 1}])
def test_invalid_custom_types(client, value):
    response = client.post('/api/id/', json={
        'url': 'https://example.com', 'custom_id': value})
    assert response.status_code == 400
    assert URLMap.query.count() == 0


def test_collision_retry(client, monkeypatch):
    URLMap.create('https://example.com/first', 'aaaaaa')
    values = iter('aaaaaabbbbbb')
    monkeypatch.setattr('yacut.models.secrets.choice', lambda _: next(values))
    item = URLMap.create('https://example.com/second')
    assert item.short == 'bbbbbb'
    assert URLMap.get('aaaaaa').original.endswith('/first')


def test_files_empty(client):
    assert 'multiple' in client.get('/files').get_data(as_text=True)
    response = client.post('/files', data={})
    assert 'Выберите хотя бы один файл.' in response.get_data(as_text=True)
    assert URLMap.query.count() == 0


def test_files_missing_token(client, monkeypatch):
    monkeypatch.setitem(app.config, 'DISK_TOKEN', '')
    response = client.post('/files', data={
        'files': (BytesIO(b'hello'), 'test.txt')})
    assert response.status_code == 200
    assert 'DISK_TOKEN' in response.get_data(as_text=True)
    assert URLMap.query.count() == 0


def test_partial_upload(client, monkeypatch):
    upload = AsyncMock(return_value=[
        ('<sample>.txt', 'https://download.example/file1'),
        RuntimeError('upstream failed'),
        ('third.txt', 'https://download.example/file3')])
    monkeypatch.setattr('yacut.views.upload_files', upload)
    response = client.post('/files', data={'files': [
        (BytesIO(b'a'), '<sample>.txt'), (BytesIO(b'b'), 'second.txt'),
        (BytesIO(b'c'), 'third.txt')]})
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert '&lt;sample&gt;.txt' in html
    assert 'Не удалось загрузить second.txt' in html
    items = URLMap.query.all()
    assert len(items) == 2
    assert len({item.short for item in items}) == 2
    for item in items:
        assert len(item.short) == 6
        assert client.get('/' + item.short).location == item.original


def test_concurrent_http_flow(default_app, monkeypatch):
    monkeypatch.setitem(app.config, 'DISK_TOKEN', 'test-token')
    calls = []
    active = 0
    peak = 0

    class Response:
        def __init__(self, body=None, headers=None):
            self.body = body
            self.headers = headers or {}

        async def __aenter__(self):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0)
            return self

        async def __aexit__(self, *args):
            nonlocal active
            active -= 1

        def raise_for_status(self):
            pass

        async def json(self):
            return self.body

    class Session:
        def __init__(self, **kwargs):
            assert 'headers' not in kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def get(self, url, **kwargs):
            calls.append((url, kwargs))
            assert kwargs['headers']['Authorization'] == 'OAuth test-token'
            if url.endswith('/upload'):
                return Response({'href': 'https://upload.example/file'})
            assert kwargs['params']['path'] == '/Apps/my file.txt'
            return Response({'href': 'https://download.example/test.txt'})

        def put(self, url, **kwargs):
            assert 'headers' not in kwargs
            assert kwargs['data'].read() == b'payload'
            return Response(headers={'Location': '/disk/Apps/my%20file.txt'})

    monkeypatch.setattr(disk.aiohttp, 'ClientSession', Session)
    files = [FileStorage(BytesIO(b'payload'), filename='test.txt')
             for _ in range(2)]
    results = asyncio.run(disk.upload_files(files))
    assert results == [('test.txt', 'https://download.example/test.txt')] * 2
    assert peak >= 2
    paths = [kwargs['params']['path'] for url, kwargs in calls
             if url.endswith('/upload')]
    assert len(set(paths)) == 2
    assert all(path.startswith('app:/') for path in paths)


def test_csrf(client, monkeypatch):
    monkeypatch.setitem(app.config, 'WTF_CSRF_ENABLED', True)
    response = client.post('/', data={'original_link': 'https://example.com'})
    assert 'Обновите страницу' in response.get_data(as_text=True)
    assert URLMap.query.count() == 0


def test_malformed_json(client):
    response = client.post('/api/id/', data='{',
                           content_type='application/json')
    assert response.status_code == 400
    assert 'message' in response.json
