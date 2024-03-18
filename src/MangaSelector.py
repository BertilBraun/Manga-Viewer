from typing import Sequence
import tkinter as tk
from tkinter import ttk
from src.util import log
from src.Manga import Manga
from src.MangaViewer import MangaViewer


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
