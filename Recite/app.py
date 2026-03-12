from __future__ import annotations

import re
import sys
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths, QTimer, Qt, QUrl
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

AUDIO_EXTENSIONS = (".mp3", ".wav", ".m4a", ".flac", ".ogg")
SUBTITLE_EXTENSIONS = (".lrc", ".vtt")
TAIL_SEEK_SAFETY_MS = 250
TIMESTAMP_PATTERN = re.compile(r"\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]")
VTT_CUE_TIMING_PATTERN = re.compile(
    r"^\s*((?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})\s+-->\s+((?:\d{2}:)?\d{2}:\d{2}[.,]\d{3})(?:\s+.*)?\s*$"
)


@dataclass(frozen=True)
class LyricLine:
    start_ms: int
    text: str


class ReciteWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Recite Player")
        self.resize(980, 700)
        self.settings = QSettings("AI-TTS", "RecitePlayer")

        self.audio_path: Path | None = None
        self.subtitle_path: Path | None = None
        self.lyrics: list[LyricLine] = []
        self.lyric_starts: list[int] = []
        self.current_index: int = -1
        self.continuous_mode: bool = False
        self.continuous_paused: bool = False
        self.paused_during_gap: bool = False
        self.current_repeat: int = 0
        self.user_seeking: bool = False

        self.audio_output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(self._on_player_position_changed)
        self.player.durationChanged.connect(self._on_player_duration_changed)

        self.stop_timer = QTimer(self)
        self.stop_timer.setInterval(20)
        self.stop_timer.timeout.connect(self._check_line_end)

        self.gap_timer = QTimer(self)
        self.gap_timer.setSingleShot(True)
        self.gap_timer.timeout.connect(self._play_current_line_for_continuous)

        self._build_ui()
        self._bind_shortcuts()

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)

        top_row = QHBoxLayout()
        self.file_label = QLabel("Select an audio or subtitle file to start.")
        self.file_label.setWordWrap(True)
        open_button = QPushButton("Open File")
        open_button.clicked.connect(self.open_file)
        self.show_text_checkbox = QCheckBox("Show Original Text")
        self.show_text_checkbox.setChecked(False)
        self.show_text_checkbox.toggled.connect(self.refresh_lyrics_display)
        self.show_preview_words_checkbox = QCheckBox("Show Preview Words")
        self.show_preview_words_checkbox.setChecked(False)
        self.show_preview_words_checkbox.toggled.connect(
            self.refresh_lyrics_display)

        top_row.addWidget(open_button)
        top_row.addWidget(self.show_text_checkbox)
        top_row.addWidget(self.show_preview_words_checkbox)
        top_row.addStretch(1)
        layout.addLayout(top_row)
        layout.addWidget(self.file_label)

        self.current_line_label = QLabel("")
        self.current_line_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_line_label.setWordWrap(True)
        self.current_line_label.setMinimumHeight(100)
        self.current_line_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.current_line_label.setStyleSheet(
            "font-size: 24px; font-weight: 600; padding: 8px;")
        layout.addWidget(self.current_line_label)

        self.lyrics_list = QListWidget()
        self.lyrics_list.setWordWrap(True)
        self.lyrics_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.lyrics_list.itemDoubleClicked.connect(
            self._on_item_double_clicked)
        layout.addWidget(self.lyrics_list)

        progress_row = QHBoxLayout()
        self.elapsed_label = QLabel("00:00")
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 0)
        self.progress_slider.sliderPressed.connect(self._on_seek_slider_pressed)
        self.progress_slider.sliderReleased.connect(
            self._on_seek_slider_released)
        self.progress_slider.sliderMoved.connect(self._on_seek_slider_moved)
        self.total_label = QLabel("00:00")
        progress_row.addWidget(self.elapsed_label)
        progress_row.addWidget(self.progress_slider, 1)
        progress_row.addWidget(self.total_label)
        layout.addLayout(progress_row)

        controls = QHBoxLayout()
        self.prev_button = QPushButton("Previous (↑)")
        self.replay_button = QPushButton("Replay (Space)")
        self.next_button = QPushButton("Next (↓)")

        self.prev_button.clicked.connect(self.play_previous_line)
        self.replay_button.clicked.connect(self.replay_current_line)
        self.next_button.clicked.connect(self.play_next_line)
        self.speed_label = QLabel("Speed: 1.00x")
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(50, 150)
        self.speed_slider.setValue(100)
        self.speed_slider.setFixedWidth(180)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)

        controls.addWidget(self.prev_button)
        controls.addWidget(self.replay_button)
        controls.addWidget(self.next_button)
        controls.addStretch(1)
        controls.addWidget(self.speed_label)
        controls.addWidget(self.speed_slider)
        layout.addLayout(controls)

        continuous_controls = QHBoxLayout()
        self.continuous_button = QPushButton("Play Continuous")
        self.continuous_button.clicked.connect(self.toggle_continuous_play)
        self.stop_continuous_button = QPushButton("Stop Continuous")
        self.stop_continuous_button.clicked.connect(self.stop_continuous_play)
        self.repeat_label = QLabel("Repeat each subtitle:")
        self.repeat_spin = QSpinBox()
        self.repeat_spin.setRange(1, 20)
        self.repeat_spin.setValue(3)
        self.gap_label = QLabel("Gap (ms):")
        self.gap_spin = QSpinBox()
        self.gap_spin.setRange(0, 10000)
        self.gap_spin.setSingleStep(100)
        self.gap_spin.setValue(500)

        continuous_controls.addWidget(self.continuous_button)
        continuous_controls.addWidget(self.stop_continuous_button)
        continuous_controls.addStretch(1)
        continuous_controls.addWidget(self.repeat_label)
        continuous_controls.addWidget(self.repeat_spin)
        continuous_controls.addWidget(self.gap_label)
        continuous_controls.addWidget(self.gap_spin)
        layout.addLayout(continuous_controls)

    def _on_speed_changed(self, value: int) -> None:
        rate = value / 100.0
        self.player.setPlaybackRate(rate)
        self.speed_label.setText(f"Speed: {rate:.2f}x")

    def _bind_shortcuts(self) -> None:
        QShortcut(QKeySequence(Qt.Key.Key_Up), self,
                  activated=self.play_previous_line)
        QShortcut(QKeySequence(Qt.Key.Key_Down),
                  self, activated=self.play_next_line)
        QShortcut(QKeySequence(Qt.Key.Key_Space), self,
                  activated=self.replay_current_line)

    def open_file(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio or Subtitle File",
            self._initial_open_dir(),
            "Audio/Subtitle Files (*.mp3 *.wav *.m4a *.flac *.ogg *.lrc *.vtt);;All Files (*)",
        )
        if not selected:
            return

        chosen = Path(selected)
        self._save_last_open_dir(chosen.parent)
        pair = self._find_pair(chosen)
        if pair is None:
            QMessageBox.warning(
                self,
                "Missing Corresponding File",
                "Cannot find matching audio/subtitle files with the same name in this folder.",
            )
            return

        audio_file, subtitle_file = pair
        self._load_pair(audio_file, subtitle_file)

    def _initial_open_dir(self) -> str:
        saved_dir = self.settings.value("last_open_dir", "", str)
        if saved_dir and Path(saved_dir).exists():
            return saved_dir

        docs_dir = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation)
        if docs_dir and Path(docs_dir).exists():
            return docs_dir

        return str(Path.home())

    def _save_last_open_dir(self, folder: Path) -> None:
        if folder.exists():
            self.settings.setValue("last_open_dir", str(folder))

    def _find_pair(self, selected_path: Path) -> tuple[Path, Path] | None:
        suffix = selected_path.suffix.lower()
        stem_path = selected_path.with_suffix("")

        if suffix in SUBTITLE_EXTENSIONS:
            for ext in AUDIO_EXTENSIONS:
                candidate_audio = stem_path.with_suffix(ext)
                if candidate_audio.exists():
                    return candidate_audio, selected_path
            return None

        if suffix in AUDIO_EXTENSIONS:
            for subtitle_ext in SUBTITLE_EXTENSIONS:
                candidate_subtitle = stem_path.with_suffix(subtitle_ext)
                if candidate_subtitle.exists():
                    return selected_path, candidate_subtitle
            return None

        return None

    def _load_pair(self, audio_file: Path, subtitle_file: Path) -> None:
        lyrics = self._parse_subtitle(subtitle_file)
        if not lyrics:
            QMessageBox.warning(
                self,
                "No Timed Lines",
                "The selected subtitle file has no valid timed lines.",
            )
            return

        self.audio_path = audio_file
        self.subtitle_path = subtitle_file
        self.lyrics = lyrics
        self.lyric_starts = [line.start_ms for line in lyrics]
        self.current_index = 0
        self._end_continuous_mode(reset_index=False)

        self.player.setSource(QUrl.fromLocalFile(str(audio_file)))
        self.player.pause()

        self.file_label.setText(
            f"Audio: {audio_file.name}    Subtitle: {subtitle_file.name}")
        self.refresh_lyrics_display()
        self._select_index(0)
        self.replay_current_line()

    def _parse_subtitle(self, subtitle_file: Path) -> list[LyricLine]:
        suffix = subtitle_file.suffix.lower()
        if suffix == ".vtt":
            return self._parse_vtt(subtitle_file)
        return self._parse_lrc(subtitle_file)

    def _parse_lrc(self, lrc_file: Path) -> list[LyricLine]:
        parsed_lines: list[LyricLine] = []
        for raw_line in lrc_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            matches = list(TIMESTAMP_PATTERN.finditer(raw_line))
            if not matches or matches[0].start() != 0:
                continue

            text = raw_line[matches[-1].end():].strip()
            for m in matches:
                start_ms = self._timestamp_to_ms(
                    m.group(1), m.group(2), m.group(3))
                parsed_lines.append(LyricLine(start_ms=start_ms, text=text))

        parsed_lines.sort(key=lambda x: x.start_ms)
        return parsed_lines

    def _parse_vtt(self, vtt_file: Path) -> list[LyricLine]:
        lines = vtt_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        parsed_lines: list[LyricLine] = []
        i = 0

        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            upper = line.upper()
            if upper == "WEBVTT":
                i += 1
                continue
            if upper.startswith("NOTE"):
                i += 1
                while i < len(lines) and lines[i].strip():
                    i += 1
                continue
            if upper.startswith("STYLE") or upper.startswith("REGION"):
                i += 1
                while i < len(lines) and lines[i].strip():
                    i += 1
                continue

            timing_line = line
            timing_match = VTT_CUE_TIMING_PATTERN.match(timing_line)
            if timing_match is None and i + 1 < len(lines):
                candidate_timing = lines[i + 1].strip()
                timing_match = VTT_CUE_TIMING_PATTERN.match(candidate_timing)
                if timing_match is not None:
                    i += 1
                    timing_line = candidate_timing

            if timing_match is None:
                i += 1
                continue

            start_ms = self._vtt_timestamp_to_ms(timing_match.group(1))
            i += 1
            text_lines: list[str] = []
            while i < len(lines) and lines[i].strip():
                text_lines.append(lines[i].strip())
                i += 1

            text = " ".join(text_lines).strip()
            if text:
                parsed_lines.append(LyricLine(start_ms=start_ms, text=text))

        parsed_lines.sort(key=lambda x: x.start_ms)
        return parsed_lines

    @staticmethod
    def _vtt_timestamp_to_ms(timestamp: str) -> int:
        normalized = timestamp.replace(",", ".")
        parts = normalized.split(":")
        if len(parts) == 2:
            hours = 0
            minutes = int(parts[0])
            sec_part = parts[1]
        else:
            hours = int(parts[0])
            minutes = int(parts[1])
            sec_part = parts[2]

        seconds_str, millis_str = sec_part.split(".", 1)
        seconds = int(seconds_str)
        millis = int((millis_str + "000")[:3])
        return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis

    @staticmethod
    def _timestamp_to_ms(minutes: str, seconds: str, fraction: str | None) -> int:
        mm = int(minutes)
        ss = int(seconds)
        frac = fraction or "0"
        if len(frac) == 1:
            ms = int(frac) * 100
        elif len(frac) == 2:
            ms = int(frac) * 10
        else:
            ms = int(frac[:3])
        return (mm * 60 + ss) * 1000 + ms

    def refresh_lyrics_display(self) -> None:
        self.lyrics_list.clear()
        show_text = self.show_text_checkbox.isChecked()
        show_preview_words = self.show_preview_words_checkbox.isChecked()
        for idx, line in enumerate(self.lyrics):
            ts = self._format_ms(line.start_ms)
            if show_text:
                line_text = f"{ts}  {line.text}"
            elif show_preview_words:
                words = line.text.split()
                if len(words) >= 3:
                    preview_text = " ".join(words[:3])
                elif words:
                    preview_text = words[0]
                else:
                    preview_text = ""
                line_text = f"{ts}  {preview_text}" if preview_text else ts
            else:
                line_text = ts
            item = QListWidgetItem(line_text)
            item.setData(Qt.ItemDataRole.UserRole, idx)
            self.lyrics_list.addItem(item)

        if 0 <= self.current_index < len(self.lyrics):
            self._select_index(self.current_index)

    @staticmethod
    def _format_ms(ms: int) -> str:
        total_seconds = ms // 1000
        mm = total_seconds // 60
        ss = total_seconds % 60
        cc = (ms % 1000) // 10
        return f"[{mm:02d}:{ss:02d}.{cc:02d}]"

    @staticmethod
    def _format_mmss(ms: int) -> str:
        total_seconds = max(0, ms) // 1000
        mm = total_seconds // 60
        ss = total_seconds % 60
        return f"{mm:02d}:{ss:02d}"

    def _on_player_duration_changed(self, duration_ms: int) -> None:
        self.progress_slider.setRange(0, max(0, duration_ms))
        self.total_label.setText(self._format_mmss(duration_ms))

    def _on_player_position_changed(self, position_ms: int) -> None:
        if not self.user_seeking:
            self.progress_slider.setValue(max(0, position_ms))
        self.elapsed_label.setText(self._format_mmss(position_ms))
        if not self.stop_timer.isActive():
            self._sync_index_to_position(position_ms)

    def _on_seek_slider_pressed(self) -> None:
        self.user_seeking = True

    def _on_seek_slider_moved(self, position_ms: int) -> None:
        self.elapsed_label.setText(self._format_mmss(position_ms))
        self._sync_index_to_position(position_ms)

    def _on_seek_slider_released(self) -> None:
        self.user_seeking = False
        new_pos = self.progress_slider.value()
        self.player.setPosition(new_pos)
        self.elapsed_label.setText(self._format_mmss(new_pos))
        self._sync_index_to_position(new_pos)
        if self.continuous_mode:
            self.current_repeat = 0

    def _sync_index_to_position(self, position_ms: int) -> None:
        if not self.lyric_starts:
            return
        idx = bisect_right(self.lyric_starts, max(0, position_ms)) - 1
        if idx < 0:
            idx = 0
        if idx != self.current_index and 0 <= idx < len(self.lyrics):
            self._select_index(idx)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        index = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(index, int):
            self.current_index = index
            self._select_index(index)
            self.replay_current_line()

    def _select_index(self, index: int) -> None:
        if not (0 <= index < len(self.lyrics)):
            return

        self.current_index = index
        self.lyrics_list.setCurrentRow(index)

        if self.show_text_checkbox.isChecked():
            self.current_line_label.setText(self.lyrics[index].text)
        else:
            self.current_line_label.setText("")

    def _line_end_ms(self, index: int) -> int:
        if index + 1 < len(self.lyrics):
            return self.lyrics[index + 1].start_ms

        duration = self.player.duration()
        if duration > self.lyrics[index].start_ms:
            return duration
        return self.lyrics[index].start_ms + 4000

    def replay_current_line(self) -> None:
        if not self.lyrics:
            return
        if self.current_index < 0:
            self.current_index = 0

        self._end_continuous_mode(reset_index=False)
        self._select_index(self.current_index)
        start_ms = self.lyrics[self.current_index].start_ms
        if self._seek_and_play(start_ms):
            self.stop_timer.start()

    def play_next_line(self) -> None:
        if not self.lyrics:
            return
        self._end_continuous_mode(reset_index=False)
        next_index = min(self.current_index + 1, len(self.lyrics) - 1)
        self.current_index = next_index
        self.replay_current_line()

    def play_previous_line(self) -> None:
        if not self.lyrics:
            return
        self._end_continuous_mode(reset_index=False)
        prev_index = max(self.current_index - 1, 0)
        self.current_index = prev_index
        self.replay_current_line()

    def toggle_continuous_play(self) -> None:
        if not self.lyrics:
            return

        if not self.continuous_mode:
            self.start_continuous_play()
            return

        if self.continuous_paused:
            self.resume_continuous_play()
        else:
            self.pause_continuous_play()

    def start_continuous_play(self) -> None:
        if not self.lyrics:
            return

        if self.current_index < 0 or self.current_index >= len(self.lyrics):
            self.current_index = 0

        self.continuous_mode = True
        self.continuous_paused = False
        self.paused_during_gap = False
        self.current_repeat = 0
        self.continuous_button.setText("Pause Continuous")
        self._play_current_line_for_continuous()

    def pause_continuous_play(self) -> None:
        if not self.continuous_mode:
            return

        self.continuous_paused = True
        if self.gap_timer.isActive():
            self.gap_timer.stop()
            self.paused_during_gap = True
        else:
            self.player.pause()
            self.stop_timer.stop()
        self.continuous_button.setText("Resume Continuous")

    def resume_continuous_play(self) -> None:
        if not self.continuous_mode:
            return

        self.continuous_paused = False
        self.continuous_button.setText("Pause Continuous")
        if self.paused_during_gap:
            self.paused_during_gap = False
            self._start_gap_timer()
            return

        self.player.play()
        self.stop_timer.start()

    def stop_continuous_play(self) -> None:
        if not self.lyrics:
            return
        self._end_continuous_mode(reset_index=True)

    def _end_continuous_mode(self, reset_index: bool) -> None:
        self.continuous_mode = False
        self.continuous_paused = False
        self.paused_during_gap = False
        self.current_repeat = 0
        self.gap_timer.stop()
        self.stop_timer.stop()
        self.player.pause()
        self.continuous_button.setText("Play Continuous")

        if reset_index and self.lyrics:
            self.current_index = 0
            self._select_index(0)

    def _play_current_line_for_continuous(self) -> None:
        if not self.continuous_mode or self.continuous_paused:
            return
        if not (0 <= self.current_index < len(self.lyrics)):
            self._end_continuous_mode(reset_index=False)
            return

        self._select_index(self.current_index)
        start_ms = self.lyrics[self.current_index].start_ms
        if self._seek_and_play(start_ms):
            self.stop_timer.start()

    def _seek_and_play(self, requested_start_ms: int) -> bool:
        duration = self.player.duration()
        if duration > 0:
            # MP3 decoders can emit timestamp warnings when seeking in the tail.
            safe_last_start = max(0, duration - TAIL_SEEK_SAFETY_MS)
            if requested_start_ms >= duration:
                self.player.setPosition(safe_last_start)
                self.player.pause()
                return False
            start_ms = min(requested_start_ms, safe_last_start)
        else:
            start_ms = max(0, requested_start_ms)

        self.player.setPosition(start_ms)
        self.player.play()
        return True

    def _start_gap_timer(self) -> None:
        if not self.continuous_mode or self.continuous_paused:
            return
        gap_ms = max(0, self.gap_spin.value())
        if gap_ms == 0:
            self._play_current_line_for_continuous()
            return
        self.gap_timer.start(gap_ms)

    def _check_line_end(self) -> None:
        if not self.lyrics or self.current_index < 0:
            self.stop_timer.stop()
            return

        if self.player.position() >= self._line_end_ms(self.current_index):
            self.player.pause()
            self.stop_timer.stop()
            if not self.continuous_mode or self.continuous_paused:
                return

            repeat_target = max(1, self.repeat_spin.value())
            if self.current_repeat + 1 < repeat_target:
                self.current_repeat += 1
                self._play_current_line_for_continuous()
                return

            self.current_repeat = 0
            if self.current_index + 1 < len(self.lyrics):
                self.current_index += 1
                self._start_gap_timer()
                return

            self._end_continuous_mode(reset_index=False)


def main() -> int:
    app = QApplication(sys.argv)
    window = ReciteWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
