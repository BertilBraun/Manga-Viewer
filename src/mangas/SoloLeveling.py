from src.Manga import Manga, prefetch_all_chapters
from src.util import fetch
from bs4 import BeautifulSoup


class SoloLeveling(Manga):
    BASE_URL = 'https://www.solo-leveling-manhwa.com/solo-leveling-chapter-{chapter}'

    def __init__(self):
        super().__init__('Solo Leveling')

    def get_image_urls(self, chapter: str) -> list[str]:
        response = fetch(SoloLeveling.BASE_URL.format(chapter=chapter))
        soup = BeautifulSoup(response, 'html.parser')

        image_tags = soup.find_all('img')

        image_urls = [img['src'] for img in image_tags if 'imgur' in img['src']]
        return image_urls

    def get_all_chapters(self) -> list[str]:
        return [str(i) for i in range(201)]


if __name__ == '__main__':
    prefetch_all_chapters(SoloLeveling())
