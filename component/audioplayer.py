import os
import shutil

from PySide6.QtCore import Qt, QUrl, QRectF, Signal, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QIcon
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QMenu, QSlider, QVBoxLayout,
    QInputDialog, QStyle
)


def format_time(ms) -> str:
    ms = max(int(ms or 0), 0)
    total_seconds = int(ms / 1000)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


APP_BG = "#0A0A0A"
CARD_BG = "#131316"
BORDER = "#26262B"
TEXT = "#ECEDEE"
MUTED = "#8A8A8F"
ACCENT = "#FF6B1A"   # vibrant orange accent
ACCENT_HOVER = "#FF8A3D"
ACCENT_PRESSED = "#E0550E"
ON_ACCENT = "#1B0A02"  # near-black glyph used on top of the orange buttons


class IconButton(QFrame):
    """A round icon button using Qt's built-in standard icons, with hover and
    press feedback (no focus rectangle)."""
    clicked = Signal()

    # kind -> standard pixmap (play/stop/download use built-ins; menu is drawn)
    _STD = {
        "play": QStyle.StandardPixmap.SP_MediaPlay,
        "stop": QStyle.StandardPixmap.SP_MediaStop,
        "download": QStyle.StandardPixmap.SP_DialogSaveButton,
    }

    def __init__(self, parent=None, size=34, kind="play"):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("IconButton")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._playing = False
        self._kind = kind
        self._hover = False
        self._pressed = False

    def set_playing(self, playing: bool):
        if self._playing != playing:
            self._playing = playing
            self.update()

    def set_kind(self, kind):
        self._kind = kind
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self.update()
            # Pulse back to idle so the user sees they clicked.
            QTimer.singleShot(130, self._release_press)
            self.clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)

    def _release_press(self):
        if self._pressed:
            self._pressed = False
            self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self._pressed = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)

        # The play button is the primary control — solid orange circle.
        # Others keep a subtle monochrome look with orange hover/press accents.
        if self._kind == "play":
            if self._pressed:
                bg, border = ACCENT_PRESSED, ACCENT_PRESSED
            elif self._hover:
                bg, border = ACCENT_HOVER, ACCENT_HOVER
            else:
                bg, border = ACCENT, ACCENT
        else:
            bg = CARD_BG
            border = BORDER
            if self._pressed:
                bg, border = ACCENT_PRESSED, ACCENT
            elif self._hover:
                bg, border = "#1B1B1F", ACCENT

        p.setBrush(QColor(bg))
        p.setPen(QColor(border))
        p.drawEllipse(r)
        p.setPen(Qt.PenStyle.NoPen)

        cx, cy = r.center().x(), r.center().y()
        scale = 1.10 if self._pressed else 1.0

        if self._kind == "play":
            # Hand-drawn play triangle, dark for contrast on the orange fill.
            s = r.width() * 0.42 * scale
            path = QPainterPath()
            x0 = cx - s * 0.15
            path.moveTo(x0, cy - s * 0.55)
            path.lineTo(x0, cy + s * 0.55)
            path.lineTo(x0 + s * 0.95, cy)
            path.closeSubpath()
            p.setBrush(QColor(ON_ACCENT))
            p.drawPath(path)
        elif self._kind in self._STD:
            icon = self.style().standardIcon(self._STD[self._kind])
            if icon.isNull():
                self._draw_placeholder(p, cx, cy, r)
            else:
                s = int(r.width() * 0.52 * scale)
                pix = icon.pixmap(s, s)
                # Tint the standard icon so it reads on the dark circle.
                tint = QColor(TEXT)
                if pix.isNull():
                    self._draw_placeholder(p, cx, cy, r)
                else:
                    tp = self._tinted_pixmap(pix, tint)
                    p.drawPixmap(int(cx - s / 2), int(cy - s / 2), tp)
        elif self._kind == "menu":
            # Clean, centered horizontal three-dot overflow glyph.
            p.setBrush(QColor(TEXT))
            d = r.width() * 0.11 * scale
            gap = r.width() * 0.17
            for i in range(3):
                x = cx + (i - 1) * gap
                p.drawEllipse(QRectF(x - d, cy - d, d * 2, d * 2))
        p.end()

    @staticmethod
    def _tinted_pixmap(pix, color):
        """Recolor a standard icon's alpha mask to `color` for a consistent look."""
        from PySide6.QtGui import QPixmap, QPainter as _QP
        tinted = QPixmap(pix.size())
        tinted.fill(Qt.GlobalColor.transparent)
        tp = _QP(tinted)
        tp.setCompositionMode(_QP.CompositionMode.CompositionMode_Source)
        tp.fillRect(tinted.rect(), QColor(color))
        tp.setCompositionMode(_QP.CompositionMode.CompositionMode_DestinationIn)
        tp.drawPixmap(0, 0, pix)
        tp.end()
        return tinted

    def _draw_placeholder(self, p, cx, cy, r):
        """Fallback so a button never renders empty if an icon is missing."""
        p.setBrush(QColor(TEXT))
        d = r.width() * 0.14
        for i in range(3):
            x = cx + (i - 1) * r.width() * 0.17
            p.drawEllipse(QRectF(x - d, cy - d, d * 2, d * 2))



class AudioPlayer(QFrame):
    """Slim, slick bottom player.

    Layout (single compact row):
      [play/pause]  title · OLED TTS    0:00 / 0:00  [download]
       ---------------- seek slider -------------------------------
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AudioPlayer")

        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._audio_output.setVolume(0.9)
        self._player.setAudioOutput(self._audio_output)

        self._path = None
        self._seeking = False
        self._streaming = False
        self._stream_timer = QTimer(self)
        self._stream_timer.setInterval(500)
        self._stream_timer.timeout.connect(self._on_stream_timeout)

        self._build_ui()
        self.apply_styles()

        self.play_btn.clicked.connect(self.toggle_playback)
        self.stop_btn.clicked.connect(self.stop)
        self.download_btn.clicked.connect(self.download)
        self.menu_btn.clicked.connect(self.open_menu)
        self.slider.sliderPressed.connect(self._on_slider_pressed)
        self.slider.sliderReleased.connect(self._on_slider_released)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.playbackStateChanged.connect(self._on_state_changed)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 6, 12, 6)
        outer.setSpacing(4)

        row1 = QHBoxLayout()
        row1.setSpacing(10)

        self.play_btn = IconButton(kind="play", size=34)
        self.stop_btn = IconButton(kind="stop", size=26)
        self.download_btn = IconButton(kind="download", size=26)
        self.menu_btn = IconButton(kind="menu", size=26)

        info = QVBoxLayout()
        info.setSpacing(0)
        self.label_title = QLabel("No audio generated yet")
        self.label_title.setObjectName("TrackLabel")
        info.addWidget(self.label_title)

        self.label_time = QLabel("0:00 / 0:00")
        self.label_time.setObjectName("TimeLabel")

        row1.addWidget(self.play_btn)
        row1.addWidget(self.stop_btn)
        row1.addLayout(info, 1)
        row1.addWidget(self.label_time, 0, Qt.AlignmentFlag.AlignVCenter)
        row1.addWidget(self.download_btn)
        row1.addWidget(self.menu_btn)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setObjectName("SeekSlider")
        self.slider.setRange(0, 0)
        self.slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider.setFixedHeight(4)

        outer.addLayout(row1)
        outer.addWidget(self.slider)

        self.setFixedHeight(56)

    # -- public API ---------------------------------------------------------
    def load(self, path, autoplay=True):
        """Load a finalized audio file (after generation completes)."""
        if not path or not os.path.exists(str(path)):
            return self._mark_missing()
        self._player.stop()
        self._stream_timer.stop()
        self._path = str(path)
        self._streaming = False
        self._player.setSource(QUrl.fromLocalFile(self._path))
        self.label_title.setText(os.path.basename(self._path))
        self.slider.setRange(0, 0)
        self.label_time.setText("0:00 / 0:00")
        self.play_btn.set_kind("play")
        self.play_btn.set_playing(False)
        if autoplay:
            self.play()
        return True

    def load_live(self, path):
        """Start playing a growing WAV immediately during generation."""
        if not path or not os.path.exists(str(path)):
            return False
        self._player.stop()
        self._path = str(path)
        self._streaming = True
        # Re-attach source so duration/position refresh as the file grows.
        self._player.setSource(QUrl.fromLocalFile(self._path))
        self.label_title.setText(f"{os.path.basename(self._path)}  ·  generating…")
        self.slider.setRange(0, 0)
        self._stream_timer.start()
        self.play_btn.set_kind("play")
        self.play_btn.set_playing(False)
        self.play()
        return True

    def play(self):
        self._player.play()

    def pause(self):
        self._player.pause()

    def stop(self):
        self._player.stop()
        self.play_btn.set_playing(False)

    def toggle_playback(self):
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.pause()
        else:
            self.play()

    def download(self):
        if not self._path or not os.path.exists(self._path):
            return
        default_name = os.path.basename(self._path)
        dest, _ = QFileDialog.getSaveFileName(
            self, "Save audio", default_name, "Audio (*.wav)"
        )
        if dest:
            try:
                shutil.copyfile(self._path, dest)
                self.label_time.setText(f"Saved → {os.path.basename(dest)}")
            except OSError as e:
                self.label_time.setText("Save failed")

    def open_menu(self):
        if not self._path or not os.path.exists(self._path):
            return
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #17171A; border: 1px solid #2E2E33;
                    border-radius: 8px; padding: 6px; }
            QMenu::item { color: #ECEDEE; padding: 6px 18px; border-radius: 5px;
                          font-family: 'Inter', system-ui, sans-serif; font-size: 12px; }
            QMenu::item:selected { background-color: #2E2E33; }
        """)
        act_rename = menu.addAction("Rename audio")
        act = menu.exec(self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomRight()))
        if act == act_rename:
            self.rename_audio()

    def rename_audio(self):
        if not self._path or not os.path.exists(self._path):
            return
        new_name, ok = QInputDialog.getText(
            self, "Rename audio",
            "New file name:",
            text=os.path.splitext(os.path.basename(self._path))[0],
        )
        if not ok or not new_name.strip():
            return
        base = os.path.splitext(new_name.strip())[0] or "untitled"
        dest_dir = os.path.dirname(self._path)
        dest = os.path.join(dest_dir, f"{base}.wav")
        if dest != self._path and os.path.exists(dest):
            self.label_time.setText("Name already in use")
            return
        try:
            if dest != self._path:
                os.rename(self._path, dest)
            self._path = dest
            self.label_title.setText(os.path.basename(dest))
            # reload so playback continues from renamed file
            self._player.setSource(QUrl.fromLocalFile(self._path))
            self.label_time.setText("Renamed")
        except OSError:
            self.label_time.setText("Rename failed")

    def _mark_missing(self):
        self.label_title.setText("File not found")
        return False

    # -- handlers -----------------------------------------------------------
    def _on_position_changed(self, position_ms):
        if not self._seeking:
            self.slider.setValue(position_ms)
        self.label_time.setText(
            f"{format_time(position_ms)} / {format_time(self._player.duration())}"
        )

    def _on_duration_changed(self, duration_ms):
        self.slider.setRange(0, duration_ms)
        self.label_time.setText(
            f"{format_time(self._player.position())} / {format_time(duration_ms)}"
        )

    def _on_state_changed(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.play_btn.set_playing(playing)

    def _on_slider_pressed(self):
        self._seeking = True

    def _on_slider_released(self):
        self._seeking = False
        self._player.setPosition(self.slider.value())

    def _on_stream_timeout(self):
        if self._streaming and self._path and os.path.exists(self._path):
            file_size = os.path.getsize(self._path)
            pcm_size = max(0, file_size - 44)
            duration_ms = int(pcm_size / (24000 * 1 * 2) * 1000)
            self.slider.setRange(0, max(0, duration_ms))
            # Keep the running time label live even though the source is growing.
            pos = self._player.position()
            self.slider.setValue(pos)
            self.label_time.setText(
                f"{format_time(pos)} / {format_time(duration_ms)}"
            )
            if pos > duration_ms and duration_ms > 0:
                self._player.setPosition(0)

    def apply_styles(self):
        self.setStyleSheet(f"""
            #AudioPlayer {{
                background-color: {CARD_BG};
                border: 1px solid {BORDER};
            }}
            QLabel#TrackLabel {{
                color: {TEXT};
                font-size: 12px;
                font-weight: 600;
                font-family: 'Inter', system-ui, sans-serif;
            }}
            QLabel#TimeLabel {{
                color: {MUTED};
                font-size: 11px;
                font-family: 'Inter', system-ui, sans-serif;
            }}
            QSlider#SeekSlider::groove:horizontal {{
                height: 3px;
                background: {BORDER};
            }}
            QSlider#SeekSlider::sub-page:horizontal {{
                background: {ACCENT};
            }}
            QSlider#SeekSlider::handle:horizontal {{
                background: {TEXT};
                width: 8px;
                margin: -2px 0;
                border-radius: 4px;
            }}
            QSlider#SeekSlider::handle:horizontal:hover {{
                background: {ACCENT};
            }}
        """)