# Manga Viewer Project

## Introduction

The Manga Viewer Project is born out of a need for a more traditional and comfortable reading experience for manga enthusiasts. While most online manga platforms offer a scrollable view for reading, this can often be cumbersome, especially for readers who prefer a faster or more controlled pace. Our project transforms these scrollable manga views into a format that resembles reading a physical comic book, where readers can flip through pages at their leisure.

## Project Overview

This application transforms online manga, traditionally presented in a long, scrollable format, into a series of discrete, well-defined pages. Achieving this involves a complex process of identifying natural split points within the manga, such as blank lines or spaces between illustrations, to ensure each page is segmented appropriately for a traditional reading experience. This segmentation process is sophisticated, typically requiring around one minute per chapter due to the need for careful analysis and processing of the manga's content to determine these split points automatically.

Once processed, these pages are then displayed two at a time, side by side, emulating the experience of reading an open comic book. This format not only facilitates easier reading but also revives the cherished and familiar experience of reading physical manga or comic books in the digital age.

## Comparing Views

The following images illustrate the difference between the conventional scrollable view and our application's page-flipping approach, showcasing the enhanced reading experience provided by the Manga Viewer.

The following image is a typical online manga viewer, where the manga is presented in a long, scrollable format:

![Online Viewer](docs/OnlineViewer.png)

In contrast, the Manga Viewer displays pages side by side, much like an open comic book:

![Manga Viewer](docs/MangaViewer.png)

These visuals highlight the difference between the conventional scrollable view and our application's page-flipping approach, showcasing the enhanced reading experience provided by the Manga Viewer.

## Getting Started

First, clone the repository to your local machine:

```bash
git clone https://github.com/BertilBraun/Manga-Viewer
```

Next, navigate to the project directory:

```bash
cd Manga-Viewer
```

Then, install the required dependencies:

```bash
pip install -r requirements.txt
```

Finally, you can start the application.

```bash
python -m src
```

This will open the selection view, where you can choose a manga title and its chapter for reading. Once both are selected, the chapter view will open, displaying two pages side by side for your reading pleasure.

To prefetch all chapters, run:

```bash
python -m src.mangas.YOUR_MANGA_NAME
```

## Key Features

- **Comic Book-Like Viewing**: Pages are displayed statically side by side, allowing users to "flip" through the manga as they would with a physical comic book.
- **Asynchronous Fetching**: Given that parsing and processing manga pages can be time-consuming—approximately one minute per chapter for tested mangas—subsequent chapters are fetched asynchronously. This ensures a smoother reading experience, minimizing wait times as readers progress through chapters.
- **Prefetching Option**: For users who prefer having all chapters ready in advance, the application includes functionality to prefetch entire mangas. This feature loads all selected chapters before the reading session begins, ensuring uninterrupted reading.
- **Selection View**: Upon launching, the application presents a selection view where users can choose their desired manga and chapter. This user-friendly interface ensures ease of access to a wide range of manga titles and their respective chapters.

## Caching and Prefetching for Enhanced Efficiency

Understanding that the processing time required for splitting manga chapters can be substantial, the application implements a caching mechanism. This means that once a chapter is processed, it is saved as a series of PNG files. Therefore, subsequent accesses to the same chapter bypass the processing stage, loading the pre-split pages directly, which significantly reduces wait times and enhances the user experience.

Additionally, the application features a prefetching option. This functionality allows for the asynchronous fetching and processing of subsequent chapters in the background while the reader is engaged with the current chapter. If the next chapter has already been processed in a previous session, the application detects the cached version and loads it immediately, eliminating the need for reprocessing. This seamless background operation ensures that readers can continue to the next chapter without interruption or significant loading times.

These strategic optimizations—caching and prefetching—underscore our commitment to providing a smooth, enjoyable reading experience that mirrors the simplicity and pleasure of reading traditional comic books, while also navigating the challenges presented by digital manga's typical format.
