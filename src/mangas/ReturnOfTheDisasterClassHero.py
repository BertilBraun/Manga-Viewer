from src.Manga import Manga, prefetch_all_chapters
from src.util import fetch
from bs4 import BeautifulSoup


class ReturnOfTheDisasterClassHero(Manga):
    BASE_URL = 'https://returnofdisasterclasshero.com/manga/return-of-the-disaster-class-hero-chapter-{chapter}/'

    def __init__(self):
        super().__init__('Return of the Disaster-Class Hero')

    def get_image_urls(self, chapter: str) -> list[str]:
        response = fetch(ReturnOfTheDisasterClassHero.BASE_URL.format(chapter=chapter))
        soup = BeautifulSoup(response, 'html.parser')

        image_tags = soup.find_all('img')

        image_urls = [img['src'] for img in image_tags if 'hxmanga' in img['src']]
        return image_urls[1:]

    def get_all_chapters(self) -> list[str]:
        return [str(i) for i in range(1, 75)]


if __name__ == '__main__':
    prefetch_all_chapters(ReturnOfTheDisasterClassHero())
