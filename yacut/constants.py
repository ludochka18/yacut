import string

SHORT_ID_LENGTH = 6
MAX_GENERATION_ATTEMPTS = 100
MAX_SHORT_LENGTH = 16
MAX_URL_LENGTH = 2048
ALPHABET = string.ascii_letters + string.digits
RESERVED_IDS = {'files', 'static', 'api'}
DUPLICATE_MESSAGE = 'Предложенный вариант короткой ссылки уже существует.'
INVALID_SHORT_MESSAGE = 'Указано недопустимое имя для короткой ссылки'
DISK_API_URL = 'https://cloud-api.yandex.net/v1/disk/resources'
