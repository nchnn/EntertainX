"""A responsive grid of title tiles, used for search and genre results."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QGridLayout, QSizePolicy, QWidget

from api.images import ImageStore, get_store
from api.movies import MediaItem
from theme import theme_manager as theme
from ui.components.video.title_tile import TitleTile

GAP = 14


class TileGrid(QWidget):
    tile_entered = Signal(object)
    tile_left = Signal(object)
    item_activated = Signal(object)

    def __init__(self, store: ImageStore | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = store
        self._columns = 0
        self.tiles: list[TitleTile] = []
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(GAP)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

    def set_items(self, items: list[MediaItem]) -> None:
        for tile in self.tiles:
            self._grid.removeWidget(tile)
            tile.setParent(None)
            tile.deleteLater()
        self.tiles = []
        self._columns = 0
        store = self._store or get_store()
        for item in items:
            tile = TitleTile(item, parent=self)
            tile.entered.connect(self.tile_entered)
            tile.left.connect(self.tile_left)
            tile.activated.connect(self.item_activated)
            tile.load_image(store)
            self.tiles.append(tile)
        self._reflow(force=True)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return QSize(theme.TILE_WIDTH, super().minimumSizeHint().height())

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._reflow()

    def _reflow(self, force: bool = False) -> None:
        columns = max(1, (self.width() + GAP) // (theme.TILE_WIDTH + GAP))
        if columns == self._columns and not force:
            return
        self._columns = columns
        for index, tile in enumerate(self.tiles):
            self._grid.addWidget(tile, index // columns, index % columns)
