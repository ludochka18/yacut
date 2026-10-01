import asyncio
import ssl
from http import HTTPStatus
from urllib.parse import unquote
from uuid import uuid4

import aiohttp
import certifi
from flask import current_app

from .constants import DISK_API_URL


class DiskError(Exception):
    """A recoverable error communicating with Yandex Disk."""


async def upload_file(session, file, headers):
    # Keep Unicode filenames, but remove any path supplied by a browser.
    filename = file.filename.replace('\\', '/').rsplit('/', 1)[-1]
    unique_name = uuid4().hex + '_' + filename
    path = 'app:/' + unique_name
    async with session.get(
        f'{DISK_API_URL}/upload', headers=headers,
        params={'path': path, 'overwrite': 'false'},
    ) as response:
        if response.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            raise DiskError(
                'Проверьте DISK_TOKEN и права приложения Яндекс Диска.'
            )
        response.raise_for_status()
        upload_url = (await response.json())['href']
    # Do not send the OAuth token to the temporary upload host.
    # Python 3.9's SpooledTemporaryFile is not an aiohttp-supported IOBase.
    # Send raw bytes so Werkzeug uploads work across supported Python versions.
    async with session.put(upload_url, data=file.read()) as response:
        response.raise_for_status()
        location = response.headers.get('Location')
    if location:
        path = unquote(location)
        if path.startswith('/disk/'):
            path = path[len('/disk'):]
    async with session.get(
        f'{DISK_API_URL}/download', headers=headers, params={'path': path},
    ) as response:
        response.raise_for_status()
        download_url = (await response.json())['href']
    return filename, download_url


async def upload_files(files):
    token = current_app.config['DISK_TOKEN']
    headers = {'Authorization': f'OAuth {token}'}
    timeout = aiohttp.ClientTimeout(total=120)
    connector = aiohttp.TCPConnector(
        ssl=ssl.create_default_context(cafile=certifi.where())
    )
    async with aiohttp.ClientSession(
        timeout=timeout, connector=connector,
    ) as session:
        results = await asyncio.gather(
            *(upload_file(session, file, headers) for file in files),
            return_exceptions=True,
        )
    return results
