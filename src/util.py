from datetime import datetime
import requests


def log(*args, **kwargs):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f'[{timestamp}]', *args, **kwargs)


def fetch(url: str) -> bytes:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    response = requests.get(url, headers=headers)
    return response.content
