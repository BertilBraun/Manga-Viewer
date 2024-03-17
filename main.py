from datetime import datetime
from pathlib import Path
import requests
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from io import BytesIO
from bs4 import BeautifulSoup
from multiprocessing import Process


BASE_URL = 'https://www.solo-leveling-manhwa.com/solo-leveling-chapter-{chapter_number}'
SAVE_FOLDER = Path('solo_leveling')


def log(*args, **kwargs):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f'[{timestamp}]', *args, **kwargs)


def fetch(url: str) -> bytes:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    response = requests.get(url, headers=headers)
    return response.content


def fetch_image_urls(chapter_number: str) -> list[str]:
    response = fetch(BASE_URL.format(chapter_number=chapter_number))
    soup = BeautifulSoup(response, 'html.parser')

    # This is a simplification. You'll need to find the actual tags and classes for images
    image_tags = soup.find_all('img')

    image_urls = [img['src'] for img in image_tags if 'imgur' in img['src']]
    return image_urls


def fetch_image(image_url: str) -> Image.Image:
    response = fetch(image_url)
    image = Image.open(BytesIO(response))
    return image


def fetch_all_images(chapter_number: str) -> list[Image.Image]:
    image_urls = fetch_image_urls(chapter_number)
    images = [fetch_image(url) for url in image_urls]
    return images


def is_pixel_similar(
    pixel1: tuple[int, int, int] | None, pixel2: tuple[int, int, int] | None, threshold: int = 5
) -> bool:
    if pixel1 is None or pixel2 is None:
        return False
    return all(abs(p1 - p2) < threshold for p1, p2 in zip(pixel1, pixel2))


def is_pixel_black_or_white(pixel: tuple[int, int, int] | None, threshold: int = 20) -> bool:
    return is_pixel_similar(pixel, (0, 0, 0), threshold) or is_pixel_similar(pixel, (255, 255, 255), threshold)


def get_line_color(image: Image.Image, y: int) -> tuple[int, int, int] | None:
    """Get the color of the line at the given y coordinate."""
    width, height = image.size
    if y < 0 or y >= height:
        return None

    pixels = [image.getpixel((x, y)) for x in range(width)]

    num_similar = sum(is_pixel_similar(pixels[i], pixels[width // 2]) for i in range(width))

    if num_similar > width - 4:
        return pixels[0]

    return None


def find_cut(image: Image.Image, y: int) -> int:
    """Find the best place to cut the image at the given y coordinate."""
    width, height = image.size
    y = min(y + 600, height)

    # cut where the image is only one color and a minimum amount of pixels from the last cut (mostly only black or white)
    next_5_lines = [get_line_color(image, y + i) for i in range(5)]
    while y < height:
        if all(is_pixel_similar(next_5_lines[i], next_5_lines[2]) for i in range(5)):
            assert next_5_lines[0] is not None
            if is_pixel_black_or_white(next_5_lines[0]):
                break
        y += 1
        next_5_lines.pop(0)
        next_5_lines.append(get_line_color(image, y + 4))

    return y


def remove_leading_white_space(page: Image.Image) -> Image.Image:
    """Remove the leading white space from the image."""
    lines_to_remove = 0
    while lines_to_remove < page.height:
        line_color = get_line_color(page, lines_to_remove)
        if not is_pixel_black_or_white(line_color):
            break
        lines_to_remove += 1

    return page.crop((0, lines_to_remove, page.width, page.height))


def remove_trailing_white_space(page: Image.Image) -> Image.Image:
    """Remove the trailing white space from the image."""
    lines_to_remove = 0
    while lines_to_remove < page.height:
        line_color = get_line_color(page, page.height - lines_to_remove - 1)
        if not is_pixel_black_or_white(line_color):
            break
        lines_to_remove += 1

    return page.crop((0, 0, page.width, page.height - lines_to_remove))


def split_image_into_pages(image: Image.Image) -> list[Image.Image]:
    width, height = image.size

    pages = []
    y = 0
    while y < height:
        top = y
        y = find_cut(image, y)

        page = image.crop((0, top, width, y))

        # cut out leading and trailing white/black space (entire line is white/black)
        page = remove_leading_white_space(page)

        page = remove_trailing_white_space(page)

        if page.height < 10:
            # if no rows are left, skip the page
            continue

        pages.append(page)

    return pages


def process_images_from_chapter(chapter_number: str) -> list[Image.Image]:
    chapter_folder = SAVE_FOLDER / f'chapter_{chapter_number}'

    if chapter_folder.exists():
        # If already fetched, return the images
        paths = [file for file in chapter_folder.glob('page_*.png')]
        log(f'Found {len(paths)} pages for chapter {chapter_number}')
        paths.sort(key=lambda p: int(p.stem.split('_')[-1]))
        return [Image.open(path) for path in paths]

    log(f'Fetching images for chapter {chapter_number}')
    images = fetch_all_images(chapter_number)
    log(f'Fetched {len(images)} images for chapter {chapter_number}')

    total_height = sum(image.height for image in images)
    combined_images = Image.new('RGB', (images[0].width, total_height))
    y = 0
    for image in images:
        combined_images.paste(image, (0, y))
        y += image.height

    log(f'Combined {len(images)} images for chapter {chapter_number} into one of height {combined_images.height}')

    log(f'Splitting the combined image into pages for chapter {chapter_number}')
    pages = split_image_into_pages(combined_images)
    log(f'Split the combined image into {len(pages)} pages for chapter {chapter_number}')

    chapter_folder.mkdir(exist_ok=True, parents=True)

    combined_images.save(chapter_folder / 'combined.png')

    for i, page in enumerate(pages):
        # Save the pages to a file for future use
        page.save(chapter_folder / f'page_{i}.png')

    log(f'Saved {len(pages)} pages for chapter {chapter_number}')

    return pages


class MangaViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Manga Viewer')
        self.attributes('-fullscreen', True)  # Start in full-screen mode
        self.configure(bg='white')  # Set the background color of the window to white
        self.create_widgets()
        self.bind('<Left>', self.prev_page_event)  # Bind left arrow key to previous page
        self.bind('<Right>', self.next_page_event)  # Bind right arrow key to next page

        self.image_references = []
        self.pages = []
        self.current_page = 0
        self.chapter_number = '0'

    def create_widgets(self):
        self.canvas = tk.Canvas(
            self, background='white', width=self.winfo_screenwidth(), height=self.winfo_screenheight() - 50
        )
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
        self.chapter_input.insert(0, '0')
        self.chapter_input.pack()

        self.fetch_button = ttk.Button(self.nav_frame, text='Fetch Chapter', command=self.fetch_chapter)
        self.fetch_button.pack()

        self.image_label = ttk.Label(self)
        self.image_label.pack(expand=True)

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
        screen_width, screen_height = self.winfo_screenwidth() // 2 - 100, self.winfo_screenheight() - 50
        img_width, img_height = image.size

        # Calculate the scaling factor to fit the image within half the screen width or full height
        scale_factor = min(screen_width / img_width, screen_height / img_height)

        # Apply the scaling factor
        new_width, new_height = int(img_width * scale_factor), int(img_height * scale_factor)
        image = image.resize((new_width, new_height))

        return image

    def place_image(self, image: ImageTk.PhotoImage, x_factor: float, y_factor: float):
        x = self.winfo_screenwidth() * x_factor - image.width() // 2
        y = self.winfo_screenheight() * y_factor - image.height() // 2
        self.canvas.create_image(x, y, image=image, anchor=tk.NW)

    def fetch_and_process_next_chapter_async(self, chapter_number):
        # This is an async wrapper around your synchronous processing function.
        next_chapter_number = str(int(chapter_number) + 1)
        log(f'Starting to fetch and process chapter {next_chapter_number} in the background')
        # start in a parallel process
        process = Process(target=process_images_from_chapter, args=(next_chapter_number,))
        process.start()

    def fetch_chapter(self):
        self.chapter_number = self.chapter_input.get()
        log(f'Fetching Chapter {self.chapter_number}')
        self.pages = process_images_from_chapter(self.chapter_number)
        log(f'Fetched {len(self.pages)} pages')
        self.current_page = 0
        self.display_page()

        # Then, start fetching and processing the next chapter in the background.
        self.fetch_and_process_next_chapter_async(self.chapter_number)

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 2
            self.display_page()
        else:
            self.chapter_input.delete(0, tk.END)
            self.chapter_input.insert(0, str(int(self.chapter_number) - 1))
            self.fetch_chapter()

        if self.current_page == 0:
            self.prev_button.config(text='Previous Chapter')
        else:
            self.prev_button.config(text='Previous')

    def next_page(self):
        if self.current_page < len(self.pages) - 2:
            self.current_page += 2
            self.display_page()
        else:
            self.chapter_input.delete(0, tk.END)
            self.chapter_input.insert(0, str(int(self.chapter_number) + 1))
            self.fetch_chapter()

        if self.current_page == len(self.pages) - 2:
            self.next_button.config(text='Next Chapter')
        else:
            self.next_button.config(text='Next')

    # Event handlers for keyboard navigation
    def prev_page_event(self, event):
        self.prev_page()

    def next_page_event(self, event):
        self.next_page()


def prefetch_all_chapters():
    processes = []
    for i in range(201):
        try:
            process = Process(target=process_images_from_chapter, args=(str(i),))
            process.start()
            processes.append(process)
        except Exception as e:
            log(f'Failed to fetch chapter {i}: {e}')

        if i % 10 == 0:
            for process in processes:
                process.join()
            processes.clear()


if __name__ == '__main__':
    prefetch_all_chapters()

    app = MangaViewer()
    app.mainloop()
