from src.mangas.ReturnOfTheDisasterClassHero import ReturnOfTheDisasterClassHero
from src.mangas.SoloLeveling import SoloLeveling
from src.MangaSelector import MangaSelector

if __name__ == '__main__':
    app = MangaSelector([SoloLeveling(), ReturnOfTheDisasterClassHero()])
    app.mainloop()
