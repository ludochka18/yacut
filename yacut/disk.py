import asyncio
from urllib.parse import unquote
from uuid import uuid4

import aiohttp
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
        response.raise_for_status()
        upload_url = (await response.json())['href']
    # Do not send the OAuth token to the temporary upload host.
    async with session.put(upload_url, data=file.stream) as response:
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
    if not token:
        raise DiskError(
            'Добавьте DISK_TOKEN в .env и перезапустите сервер.'
        )
    headers = {'Authorization': f'OAuth {token}'}
    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        results = await asyncio.gather(
            *(upload_file(session, file, headers) for file in files),
            return_exceptions=True,
        )
    return results
