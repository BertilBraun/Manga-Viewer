from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Sequence
import requests
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from io import BytesIO
from bs4 import BeautifulSoup
from multiprocessing import Process


def log(*args, **kwargs):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f'[{timestamp}]', *args, **kwargs)


def fetch(url: str) -> bytes:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    response = requests.get(url, headers=headers)
    return response.content


class Manga(ABC):
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
    def find_cut(image: Image.Image, y: int) -> int:
        """Find the best place to cut the image at the given y coordinate."""
        width, height = image.size
        y = min(y + 600, height)

        # cut where the image is only one color and a minimum amount of pixels from the last cut (mostly only black or white)
        next_5_lines = [Manga.get_line_color(image, y + i) for i in range(5)]
        while y < height:
            if all(Manga.is_pixel_similar(next_5_lines[i], next_5_lines[2]) for i in range(5)):
                assert next_5_lines[0] is not None
                if Manga.is_pixel_black_or_white(next_5_lines[0]):
                    break
            y += 1
            next_5_lines.pop(0)
            next_5_lines.append(Manga.get_line_color(image, y + 4))

        return y

    @staticmethod
    def remove_leading_white_space(page: Image.Image) -> Image.Image:
        """Remove the leading white space from the image."""
        lines_to_remove = 0
        while lines_to_remove < page.height:
            line_color = Manga.get_line_color(page, lines_to_remove)
            if not Manga.is_pixel_black_or_white(line_color):
                break
            lines_to_remove += 1

        return page.crop((0, lines_to_remove, page.width, page.height))

    @staticmethod
    def remove_trailing_white_space(page: Image.Image) -> Image.Image:
        """Remove the trailing white space from the image."""
        lines_to_remove = 0
        while lines_to_remove < page.height:
            line_color = Manga.get_line_color(page, page.height - lines_to_remove - 1)
            if not Manga.is_pixel_black_or_white(line_color):
                break
            lines_to_remove += 1

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
        chapter_folder = Path(self.title) / f'chapter_{chapter}'

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


class MangaViewer(tk.Tk):
    def __init__(self, manga: Manga, chapter: str):
        super().__init__()
        self.manga = manga
        self.title('Manga Viewer')
        # Set the window to be maximized
        self.state('zoomed')
        self.configure(bg='white')  # Set the background color of the window to white
        self.canvas_width = self.winfo_screenwidth()
        self.canvas_height = self.winfo_screenheight() - 120

        self.image_references = []
        self.pages = []
        self.current_page = 0
        self.chapter = chapter

        self.bind('<Left>', lambda _: self.prev_page())  # Bind left arrow key to previous page
        self.bind('<Right>', lambda _: self.next_page())  # Bind right arrow key to next page

        self.create_widgets()
        self.fetch_chapter()

    def create_widgets(self):
        self.canvas = tk.Canvas(self, background='white', width=self.canvas_width, height=self.canvas_height)
        self.canvas.pack()

        # Container for navigation buttons
        self.nav_frame = tk.Frame(self)
        self.nav_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.prev_button = ttk.Button(self.nav_frame, text='Previous', command=self.prev_page)
        self.prev_button.pack(side=tk.LEFT, fill=tk.Y)

        self.next_button = ttk.Button(self.nav_frame, text='Next', command=self.next_page)
        self.next_button.pack(side=tk.RIGHT, fill=tk.Y)

        self.page_label_left = ttk.Label(self.nav_frame, text='Page 0/0')
        self.page_label_left.pack(side=tk.LEFT, fill=tk.Y)

        self.page_label_right = ttk.Label(self.nav_frame, text='Page 0/0')
        self.page_label_right.pack(side=tk.RIGHT, fill=tk.Y)

        self.chapter_input = ttk.Entry(self.nav_frame)
        # On enter, fetch the chapter
        self.chapter_input.bind('<Return>', lambda _: self.fetch_chapter())
        self.chapter_input.insert(0, self.chapter)
        self.chapter_input.pack()

        self.fetch_button = ttk.Button(self.nav_frame, text='Fetch Chapter', command=self.fetch_chapter)
        self.fetch_button.pack()

    def display_page(self):
        if not self.pages or self.current_page >= len(self.pages):
            return

        self.image_references.clear()
        self.canvas.delete('all')

        self.page_label_left.config(text=f'Page {self.current_page + 1}/{len(self.pages)}')
        self.page_label_right.config(text=f'Page {self.current_page + 2}/{len(self.pages)}')

        # Display the current page on the left label
        left_page_image = self.scale_image_to_screensize(self.pages[self.current_page])
        left_photo = ImageTk.PhotoImage(image=left_page_image)
        self.place_image(left_photo, 0.25, 0.5)
        self.image_references.append(left_photo)

        # If there is a next page, display it on the right label
        if self.current_page + 1 < len(self.pages):
            right_page_image = self.scale_image_to_screensize(self.pages[self.current_page + 1])
            right_photo = ImageTk.PhotoImage(image=right_page_image)
            self.place_image(right_photo, 0.75, 0.5)
            self.image_references.append(right_photo)

    def scale_image_to_screensize(self, image: Image.Image) -> Image.Image:
        """Scale and center the image based on the screen size."""
        screen_width, screen_height = self.canvas_width // 2 - 100, self.canvas_height - 10
        img_width, img_height = image.size

        # Calculate the scaling factor to fit the image within half the screen width or full height
        scale_factor = min(screen_width / img_width, screen_height / img_height)

        # Apply the scaling factor
        new_width, new_height = int(img_width * scale_factor), int(img_height * scale_factor)
        image = image.resize((new_width, new_height))

        return image

    def place_image(self, image: ImageTk.PhotoImage, x_factor: float, y_factor: float):
        x = self.canvas_width * x_factor - image.width() / 2
        y = self.canvas_height * y_factor - image.height() / 2
        self.canvas.create_image(x, y, image=image, anchor=tk.NW)

    def fetch_and_process_next_chapter_async(self, chapter):
        # This is an async wrapper around your synchronous processing function.
        next_chapter = self.manga.get_next_chapter(chapter)
        log(f'Starting to fetch and process chapter {next_chapter} in the background')
        # start in a parallel process
        process = Process(target=self.manga.process_images_from_chapter, args=(next_chapter,))
        process.start()

    def fetch_chapter(self):
        self.chapter = self.chapter_input.get()
        log(f'Fetching Chapter {self.chapter}')
        self.pages = self.manga.process_images_from_chapter(self.chapter)
        log(f'Fetched {len(self.pages)} pages')
        self.current_page = 0
        self.display_page()

        # Then, start fetching and processing the next chapter in the background.
        self.fetch_and_process_next_chapter_async(self.chapter)

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 2
            self.display_page()
        else:
            self.chapter_input.delete(0, tk.END)
            self.chapter_input.insert(0, self.manga.get_previous_chapter(self.chapter))
            self.fetch_chapter()

        if self.current_page == 0:
            self.prev_button.config(text='Previous Chapter')
        else:
            self.prev_button.config(text='Previous')
            self.next_button.config(text='Next')

    def next_page(self):
        if self.current_page < len(self.pages) - 2:
            self.current_page += 2
            self.display_page()
        else:
            self.chapter_input.delete(0, tk.END)
            self.chapter_input.insert(0, self.manga.get_next_chapter(self.chapter))
            self.fetch_chapter()

        if self.current_page == len(self.pages) - 2:
            self.next_button.config(text='Next Chapter')
        else:
            self.next_button.config(text='Next')
            self.prev_button.config(text='Previous')


class MangaSelector(tk.Tk):
    # This class is responsible for selecting a manga and a chapter to view
    # It will first display a list of mangas to choose from
    # Then, it will display a list of chapters to choose from
    # Finally, it will open the MangaViewer with the selected manga and chapter and close itself
    # The selections must be scrollable and the user should be able to select a manga and a chapter
    # The input should be buttons in two side-by-side frames

    def __init__(self, mangas: Sequence[Manga]):
        super().__init__()
        self.manga = None
        self.mangas = mangas
        self.title('Manga Selector')
        self.geometry('800x600')
        self.create_widgets()

    def create_widgets(self):
        self.manga_frame = tk.Frame(self)
        self.manga_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.chapter_frame = tk.Frame(self)
        self.chapter_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Manga selection scrollable area
        self.manga_canvas = tk.Canvas(self.manga_frame)
        self.manga_scrollbar = ttk.Scrollbar(self.manga_frame, orient='vertical', command=self.manga_canvas.yview)
        self.scrollable_manga_frame = ttk.Frame(self.manga_canvas)
        self.scrollable_manga_frame.bind(
            '<Configure>', lambda e: self.manga_canvas.configure(scrollregion=self.manga_canvas.bbox('all'))
        )
        self.manga_canvas.create_window((0, 0), window=self.scrollable_manga_frame, anchor='nw')
        self.manga_canvas.configure(yscrollcommand=self.manga_scrollbar.set)

        self.manga_canvas.bind_all('<MouseWheel>', self.on_mousewheel_manga)  # Bind mousewheel event

        self.manga_scrollbar.pack(side='right', fill='y')
        self.manga_canvas.pack(side='left', fill='both', expand=True)

        # Chapter selection scrollable area (initialized without content)
        self.chapter_canvas = tk.Canvas(self.chapter_frame)
        self.chapter_scrollbar = ttk.Scrollbar(self.chapter_frame, orient='vertical', command=self.chapter_canvas.yview)
        self.scrollable_chapter_frame = ttk.Frame(self.chapter_canvas)
        self.scrollable_chapter_frame.bind(
            '<Configure>', lambda e: self.chapter_canvas.configure(scrollregion=self.chapter_canvas.bbox('all'))
        )
        self.chapter_canvas.create_window((0, 0), window=self.scrollable_chapter_frame, anchor='nw')
        self.chapter_canvas.configure(yscrollcommand=self.chapter_scrollbar.set)

        self.chapter_canvas.bind_all('<MouseWheel>', self.on_mousewheel_chapter)  # Bind mousewheel event

        self.chapter_scrollbar.pack(side='right', fill='y')
        self.chapter_canvas.pack(side='left', fill='both', expand=True)

        # Populate manga buttons
        for manga in self.mangas:
            button = ttk.Button(
                self.scrollable_manga_frame, text=manga.title, command=lambda m=manga: self.select_manga(m)
            )
            button.pack(fill=tk.BOTH, expand=True)

    def on_mousewheel_manga(self, event):
        """Handle mouse wheel scrolling for the manga list."""
        self.manga_canvas.yview_scroll(int(-event.delta / 120), 'units')

    def on_mousewheel_chapter(self, event):
        """Handle mouse wheel scrolling for the chapter list."""
        self.chapter_canvas.yview_scroll(int(-event.delta / 120), 'units')

    def select_manga(self, manga: Manga):
        self.manga = manga

        # Clear existing chapters when a new manga is selected
        for widget in self.scrollable_chapter_frame.winfo_children():
            widget.destroy()

        # Populate chapter buttons for selected manga
        for chapter in manga.get_all_chapters():
            button = ttk.Button(
                self.scrollable_chapter_frame, text=chapter, command=lambda c=chapter: self.select_chapter(c)
            )
            button.pack(fill=tk.BOTH, expand=True)

    def select_chapter(self, chapter: str):
        if self.manga is None:
            log('No manga selected')
            return

        self.destroy()
        viewer = MangaViewer(self.manga, chapter)
        viewer.mainloop()


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


if __name__ == '__main__':
    mangas = [SoloLeveling()]

    for manga in mangas:
        pass
        # log(f'Prefetching all chapters for {manga.title}')
        # prefetch_all_chapters(manga)

    app = MangaSelector(mangas)
    app.mainloop()
