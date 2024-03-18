import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from multiprocessing import Process
from src.Manga import Manga
from src.util import log


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
