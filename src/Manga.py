from abc import ABC, abstractmethod
from multiprocessing import Process
from pathlib import Path
from PIL import Image
from io import BytesIO
from src.util import fetch, log


class Manga(ABC):
    MIN_IMAGE_HEIGHT = 400
    SLOPE_THRESHOLD = 50
    NUM_EMPTY_LINES = 5
    NUM_EMPTY_SLOPES = 20

    def __init__(self, title: str):
        self.title = title

    @abstractmethod
    def get_image_urls(self, chapter: str) -> list[str]:
        pass

    @abstractmethod
    def get_all_chapters(self) -> list[str]:
        pass

    def get_next_chapter(self, chapter: str) -> str:
        chapters = self.get_all_chapters()
        index = chapters.index(chapter)
        if index + 1 < len(chapters):
            return chapters[index + 1]
        return chapter

    def get_previous_chapter(self, chapter: str) -> str:
        chapters = self.get_all_chapters()
        index = chapters.index(chapter)
        if index - 1 >= 0:
            return chapters[index - 1]
        return chapter

    @staticmethod
    def fetch_image(image_url: str) -> Image.Image:
        response = fetch(image_url)
        image = Image.open(BytesIO(response))
        return image

    def fetch_all_images(self, chapter: str) -> list[Image.Image]:
        image_urls = self.get_image_urls(chapter)
        images = [Manga.fetch_image(url) for url in image_urls]
        return images

    @staticmethod
    def is_pixel_similar(
        pixel1: tuple[int, int, int] | None, pixel2: tuple[int, int, int] | None, threshold: int = 5
    ) -> bool:
        if pixel1 is None or pixel2 is None:
            return False
        return all(abs(p1 - p2) < threshold for p1, p2 in zip(pixel1, pixel2))

    @staticmethod
    def is_pixel_black_or_white(pixel: tuple[int, int, int] | None, threshold: int = 20) -> bool:
        return Manga.is_pixel_similar(pixel, (0, 0, 0), threshold) or Manga.is_pixel_similar(
            pixel, (255, 255, 255), threshold
        )

    @staticmethod
    def get_slope_color(
        image: Image.Image, y: int, y_offset_left: int, y_offset_right: int
    ) -> tuple[int, int, int] | None:
        """Get the color of the line at the given y coordinate which starts at y + y_offset_left and ends at y + y_offset_right."""
        width, height = image.size
        if y < 0 or y >= height:
            return None

        start = y + y_offset_left
        end = y + y_offset_right

        mid = (start + end) // 2
        comparison_pixel = image.getpixel((width // 2, mid))

        num_dissimilar = 0
        for x in range(width):
            # lerp y pos from start to end based on x percentage of width
            x_percentage = x / width
            y_pos = int((1 - x_percentage) * start + x_percentage * end)
            if y_pos < 0 or y_pos >= height:
                continue
            if not Manga.is_pixel_similar(image.getpixel((x, y_pos)), comparison_pixel):
                num_dissimilar += 1
                if num_dissimilar > 5:
                    return None

        return comparison_pixel

    @staticmethod
    def get_line_color(image: Image.Image, y: int) -> tuple[int, int, int] | None:
        """Get the color of the line at the given y coordinate."""
        width, height = image.size
        if y < 0 or y >= height:
            return None

        comparison_pixel = image.getpixel((width // 2, y))

        num_dissimilar = 0
        for x in range(width):
            if not Manga.is_pixel_similar(image.getpixel((x, y)), comparison_pixel):
                num_dissimilar += 1
                if num_dissimilar > 5:
                    return None

        return comparison_pixel

    @staticmethod
    def are_percent_of_lines_black_or_white(lines: list[tuple[int, int, int] | None], percent: float) -> bool:
        num_black_or_white = sum(Manga.is_pixel_black_or_white(line) for line in lines)
        return num_black_or_white / len(lines) >= percent

    @staticmethod
    def are_all_lines_black_or_white(lines: list[tuple[int, int, int] | None]) -> bool:
        return Manga.are_percent_of_lines_black_or_white(lines, 1.0)

    @staticmethod
    def find_cut(image: Image.Image, y: int) -> int:
        """Find the best place to cut the image at the given y coordinate."""
        width, height = image.size
        y = min(y + Manga.MIN_IMAGE_HEIGHT, height)

        # cut where the image is only one color and a minimum amount of pixels from the last cut (mostly only black or white)
        next_lines = [Manga.get_line_color(image, y + i) for i in range(Manga.NUM_EMPTY_LINES)]
        next_slopes_left = [
            Manga.get_slope_color(image, y + i, -Manga.SLOPE_THRESHOLD, Manga.SLOPE_THRESHOLD)
            for i in range(Manga.NUM_EMPTY_SLOPES)
        ]
        next_slopes_right = [
            Manga.get_slope_color(image, y + i, Manga.SLOPE_THRESHOLD, -Manga.SLOPE_THRESHOLD)
            for i in range(Manga.NUM_EMPTY_SLOPES)
        ]

        while y < height:
            if Manga.are_all_lines_black_or_white(next_lines):
                break

            if Manga.are_all_lines_black_or_white(next_slopes_left):
                # fill in the gap with the color of the line
                color = next_slopes_left[Manga.NUM_EMPTY_LINES // 2]
                assert color is not None
                for x in range(width // 2, width):
                    for i in range(Manga.SLOPE_THRESHOLD):
                        if y + i < height:
                            image.putpixel((x, y + i), color)
                break

            if Manga.are_all_lines_black_or_white(next_slopes_right):
                # fill in the gap with the color of the line
                color = next_slopes_right[Manga.NUM_EMPTY_LINES // 2]
                assert color is not None
                for x in range(width // 2):
                    for i in range(Manga.SLOPE_THRESHOLD):
                        if y + i < height:
                            image.putpixel((x, y + i), color)
                break

            y += 1

            next_lines.pop(0)
            next_lines.append(Manga.get_line_color(image, y + Manga.NUM_EMPTY_LINES - 1))
            next_slopes_left.pop(0)
            next_slopes_left.append(
                Manga.get_slope_color(
                    image, y + Manga.NUM_EMPTY_SLOPES - 1, -Manga.SLOPE_THRESHOLD, Manga.SLOPE_THRESHOLD
                )
            )
            next_slopes_right.pop(0)
            next_slopes_right.append(
                Manga.get_slope_color(
                    image, y + Manga.NUM_EMPTY_SLOPES - 1, Manga.SLOPE_THRESHOLD, -Manga.SLOPE_THRESHOLD
                )
            )

        return y

    @staticmethod
    def remove_leading_white_space(page: Image.Image) -> Image.Image:
        """Remove the leading white space from the image."""
        lines_to_remove = 0
        next_lines = [Manga.get_line_color(page, i) for i in range(Manga.NUM_EMPTY_LINES)]

        while lines_to_remove < page.height:
            if not Manga.are_percent_of_lines_black_or_white(next_lines, 0.5):
                break

            lines_to_remove += 1
            next_lines.pop(0)
            next_lines.append(Manga.get_line_color(page, lines_to_remove + Manga.NUM_EMPTY_LINES - 1))

        return page.crop((0, lines_to_remove, page.width, page.height))

    @staticmethod
    def remove_trailing_white_space(page: Image.Image) -> Image.Image:
        """Remove the trailing white space from the image."""
        lines_to_remove = 0
        next_lines = [Manga.get_line_color(page, page.height - i - 1) for i in range(Manga.NUM_EMPTY_LINES)]

        while lines_to_remove < page.height:
            if not Manga.are_percent_of_lines_black_or_white(next_lines, 0.5):
                break

            lines_to_remove += 1
            next_lines.pop(0)
            next_lines.append(Manga.get_line_color(page, page.height - lines_to_remove - Manga.NUM_EMPTY_LINES))

        return page.crop((0, 0, page.width, page.height - lines_to_remove))

    @staticmethod
    def split_image_into_pages(image: Image.Image) -> list[Image.Image]:
        width, height = image.size

        pages = []
        y = 0
        while y < height:
            top = y
            y = Manga.find_cut(image, y)

            page = image.crop((0, top, width, y))

            # cut out leading and trailing white/black space (entire line is white/black)
            page = Manga.remove_leading_white_space(page)

            page = Manga.remove_trailing_white_space(page)

            if page.height < 10:
                # if no rows are left, skip the page
                continue

            pages.append(page)

        return pages

    def process_images_from_chapter(self, chapter: str) -> list[Image.Image]:
        chapter_folder = Path('mangas') / self.title / f'chapter_{chapter}'

        if chapter_folder.exists():
            # If already fetched, return the images
            paths = [file for file in chapter_folder.glob('page_*.png')]
            log(f'Found {len(paths)} pages for chapter {chapter}')
            paths.sort(key=lambda p: int(p.stem.split('_')[-1]))
            return [Image.open(path) for path in paths]

        log(f'Fetching images for chapter {chapter}')
        images = self.fetch_all_images(chapter)
        log(f'Fetched {len(images)} images for chapter {chapter}')

        total_height = sum(image.height for image in images)
        combined_images = Image.new('RGB', (images[0].width, total_height))
        y = 0
        for image in images:
            combined_images.paste(image, (0, y))
            y += image.height

        log(f'Combined {len(images)} images for chapter {chapter} into one of height {combined_images.height}')

        log(f'Splitting the combined image into pages for chapter {chapter}')
        pages = Manga.split_image_into_pages(combined_images)
        log(f'Split the combined image into {len(pages)} pages for chapter {chapter}')

        chapter_folder.mkdir(exist_ok=True, parents=True)

        combined_images.save(chapter_folder / 'combined.png', compression_level=0)

        for i, page in enumerate(pages):
            # Save the pages to a file for future use
            page.save(chapter_folder / f'page_{i}.png', compression_level=0)

        log(f'Saved {len(pages)} pages for chapter {chapter}')

        return pages


def prefetch_all_chapters(manga: Manga) -> None:
    processes = []
    for i, chapter in enumerate(manga.get_all_chapters()):
        try:
            process = Process(target=manga.process_images_from_chapter, args=(str(chapter),))
            process.start()
            processes.append(process)
        except Exception as e:
            log(f'Failed to fetch chapter {chapter}: {e}')

        if i % 10 == 0:
            for process in processes:
                process.join()
            processes.clear()
