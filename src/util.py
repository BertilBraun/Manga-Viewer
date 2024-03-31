from datetime import datetime
import time
import requests


def log(*args, **kwargs):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f'[{timestamp}]', *args, **kwargs)


def fetch(url: str) -> bytes:
    # retry 3 times if the request fails
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    for _ in range(3):
        try:
            response = requests.get(url, headers=headers)
            return response.content
        except requests.RequestException as e:
            log(f'Error fetching {url}: {e}')
            time.sleep(20)

    raise requests.RequestException(f'Failed to fetch {url} after 3 attempts')
