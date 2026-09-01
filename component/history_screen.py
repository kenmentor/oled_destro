import os
import shutil
from PySide6.QtCore import Qt, QRect, QSize, QByteArray, QAbstractListModel, QModelIndex, Signal
from PySide6.QtWidgets import QFrame, QVBoxLayout, QListView, QStyledItemDelegate, QStyle, QStyleOptionViewItem, QFileDialog
from PySide6.QtGui import QPainter, QIcon, QPixmap, QColor
from modules.DataBase import DB
from modules.helpers import Helpers

PLAY_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#E4E4E7"><path d="M8 5v14l11-7z"/></svg>'
DOWNLOAD_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#E4E4E7"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z"/></svg>'
DELETE_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#ff453a"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>'

def create_svg_icon(svg_string: str) -> QIcon:
    pixmap = QPixmap()
    pixmap.loadFromData(QByteArray(svg_string.encode('utf-8')), "SVG")
    return QIcon(pixmap)

class AudioListModel(QAbstractListModel):
    def __init__(self, audio_items=None):
        super().__init__()
        self.audio_items = audio_items or []

    def rowCount(self, parent=QModelIndex()):
        return len(self.audio_items)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.audio_items)):
            return None
        
        row_data = self.audio_items[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return row_data[1]  # File path string
        elif role == Qt.ItemDataRole.UserRole:
            return row_data[0]  # Database ID
        return None

    def remove_item(self, row):
        self.beginRemoveRows(QModelIndex(), row, row)
        del self.audio_items[row]
        self.endRemoveRows()


class AudioItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.play_icon = create_svg_icon(PLAY_SVG)
        self.download_icon = create_svg_icon(DOWNLOAD_SVG)
        self.delete_icon = create_svg_icon(DELETE_SVG)
        self.btn_size = 28

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw backgrounds based on state
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor("#1c1c1e"))
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(option.rect, QColor("#2c2c2e"))
        else:
            painter.fillRect(option.rect, QColor("#121212"))

        # Render Text (Audio Path)
        rect = option.rect
        text_rect = QRect(rect.x() + 15, rect.y(), rect.width() - 120, rect.height())
        path_text = index.data(Qt.ItemDataRole.DisplayRole)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, path_text)

        # Paint operational button SVGs
        play_rect, download_rect, delete_rect = self._get_button_rects(rect)
        self.play_icon.paint(painter, play_rect, Qt.AlignmentFlag.AlignCenter)
        self.download_icon.paint(painter, download_rect, Qt.AlignmentFlag.AlignCenter)
        self.delete_icon.paint(painter, delete_rect, Qt.AlignmentFlag.AlignCenter)
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(100, 48)

    def _get_button_rects(self, row_rect):
        y = row_rect.y() + (row_rect.height() - self.btn_size) // 2
        right = row_rect.x() + row_rect.width()
        return (
            QRect(right - 105, y, self.btn_size, self.btn_size),
            QRect(right - 70, y, self.btn_size, self.btn_size),
            QRect(right - 35, y, self.btn_size, self.btn_size)
        )

    def editorEvent(self, event, model, option, index):
        if event.type() == event.Type.MouseButtonRelease:
            click_pos = event.position().toPoint()
            play_rect, download_rect, delete_rect = self._get_button_rects(option.rect)
            
            db_id = index.data(Qt.ItemDataRole.UserRole)
            file_path = index.data(Qt.ItemDataRole.DisplayRole)

            if play_rect.contains(click_pos):
                self.parent().play_requested(db_id, file_path)
                return True
            elif download_rect.contains(click_pos):
                self.parent().download_requested(db_id, file_path)
                return True
            elif delete_rect.contains(click_pos):
                self.parent().delete_requested(index.row(), db_id, file_path)
                return True
                
        return super().editorEvent(event, model, option, index)


class HistoryScreen(QFrame): 
    play_audio = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("HistoryScreen")
        self.database = DB("audios")
        self.helpers = Helpers()
        
        layout = QVBoxLayout(self)
        self.list_view = QListView(self)
        self.list_view.setMouseTracking(True)
        
        self.delegate = AudioItemDelegate(self)
        self.list_view.setItemDelegate(self.delegate)
        layout.addWidget(self.list_view)

        self.load_data()
        self.setStyleSheet("""
            QListView {
                background-color: #0A0A0A;
                border: 1px solid #2c2c2e;
                border-radius: 2px;
            }
                            font-family: 'Inter', system-ui, sans-serif;
            font-size: 11px;
            font-weight: 700;
            color: #48484A;
            letter-spacing: 1px;
           background-color: #0A0A0A; 
                           
        """)
    def showEvent(self, event) -> None:
        super().showEvent(event) 
        self.load_data()
    
    def load_data(self):
        data = self.database.get_path()
        self.model = AudioListModel(data)
        self.list_view.setModel(self.model)

    def play_requested(self, db_id, path):
        print(f"[PLAY] Triggering engine to process ID {db_id}: {path}")
        from component.toast import show_error, show_info
        if path and os.path.exists(path):
            self.play_audio.emit(path)
            show_info(self.window(), "Playing from history")
        else:
            show_error(self.window(), "Audio file no longer exists")

    def download_requested(self, db_id, path):
        target_dir = QFileDialog.getExistingDirectory(self, "Select Folder to Store Audio")
        if target_dir:
            try:
                shutil.copy(path, target_dir)
                print(f"[DOWNLOAD] Copied {path} to {target_dir}")
                from component.toast import show_success
                show_success(self.window(), f"Saved to {os.path.basename(target_dir)}")
            except Exception as e:
                print(f"[DOWNLOAD] Error occurred: {e}")
                from component.toast import show_error
                show_error(self.window(), f"Download failed:\n{e}")

    def delete_requested(self, row_index, db_id, path):
        print(f"[DELETE] Dropping record ID {db_id} from DB and View row index {row_index}")
        self.helpers.deleteFile(path)
        self.database.delete(db_id)
        self.model.remove_item(row_index)