#!/usr/bin/env python3
"""
Recite App - A text recitation practice application
Reads LRC files and plays corresponding MP3 files line by line,
allowing users to practice reciting each line before continuing.
"""

import sys
import os
import re
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QFileDialog,
    QSlider, QProgressBar, QFrame, QSplitter, QGroupBox, QSpacerItem,
    QSizePolicy, QMessageBox, QStyle
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QUrl
from PySide6.QtGui import QFont, QColor, QPalette, QIcon, QKeySequence, QShortcut, QAction
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput


@dataclass
class LyricLine:
    """Represents a single line in an LRC file with timestamp and text."""
    timestamp_ms: int  # Timestamp in milliseconds
    text: str
    
    @property
    def timestamp_str(self) -> str:
        """Return formatted timestamp string [MM:SS.ms]"""
        minutes = self.timestamp_ms // 60000
        seconds = (self.timestamp_ms % 60000) // 1000
        ms = (self.timestamp_ms % 1000) // 10
        return f"[{minutes:02d}:{seconds:02d}.{ms:02d}]"


class LRCParser:
    """Parser for LRC (Lyric) files."""
    
    # Regex pattern for timestamp: [MM:SS.ms] or [MM:SS:ms]
    TIMESTAMP_PATTERN = re.compile(r'\[(\d{2}):(\d{2})[.:](\d{2,3})\]')
    # Metadata patterns
    METADATA_PATTERN = re.compile(r'\[(al|ar|ti|by|offset):([^\]]*)\]')
    
    def __init__(self):
        self.metadata: dict = {}
        self.lyrics: List[LyricLine] = []
    
    def parse_file(self, filepath: str) -> Tuple[dict, List[LyricLine]]:
        """Parse an LRC file and return metadata and lyrics."""
        self.metadata = {}
        self.lyrics = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Check for metadata
            meta_match = self.METADATA_PATTERN.match(line)
            if meta_match:
                key, value = meta_match.groups()
                self.metadata[key] = value.strip()
                continue
            
            # Check for timestamp
            timestamp_match = self.TIMESTAMP_PATTERN.match(line)
            if timestamp_match:
                minutes, seconds, ms = timestamp_match.groups()
                # Handle both 2-digit and 3-digit milliseconds
                if len(ms) == 2:
                    ms = int(ms) * 10
                else:
                    ms = int(ms)
                
                timestamp_ms = int(minutes) * 60000 + int(seconds) * 1000 + ms
                text = line[timestamp_match.end():].strip()
                
                if text:  # Only add lines with actual text
                    self.lyrics.append(LyricLine(timestamp_ms, text))
        
        # Sort by timestamp
        self.lyrics.sort(key=lambda x: x.timestamp_ms)
        
        return self.metadata, self.lyrics


class ReciteMainWindow(QMainWindow):
    """Main window for the Recite application."""
    
    # Settings file path
    SETTINGS_FILE = Path(__file__).parent / "recite_settings.json"
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Recite - Text Recitation Practice")
        self.setMinimumSize(900, 700)
        
        # Initialize components
        self.lrc_parser = LRCParser()
        self.lyrics: List[LyricLine] = []
        self.metadata: dict = {}
        self.current_line_index: int = -1
        self.is_playing: bool = False
        self.audio_file: Optional[str] = None
        self.lrc_file: Optional[str] = None
        
        # Load settings
        self.settings = self.load_settings()
        
        # Media player setup
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(self.settings.get('volume', 80) / 100.0)
        
        # Set initial playback rate
        self.playback_rate = self.settings.get('playback_rate', 1.0)
        self.media_player.setPlaybackRate(self.playback_rate)
        
        # Connect media player signals
        self.media_player.positionChanged.connect(self.on_position_changed)
        self.media_player.durationChanged.connect(self.on_duration_changed)
        self.media_player.playbackStateChanged.connect(self.on_playback_state_changed)
        
        # Timer for checking playback position
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self.check_playback_position)
        
        # Setup UI
        self.setup_ui()
        self.setup_shortcuts()
        self.apply_styles()
        
    
    def setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Title and metadata section
        self.setup_header_section(main_layout)
        
        # Main content area with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Lyrics list
        left_panel = self.create_lyrics_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Current line and controls
        right_panel = self.create_control_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([400, 500])
        main_layout.addWidget(splitter, 1)
        
        # Bottom controls
        self.setup_bottom_controls(main_layout)

        self.setMinimumSize(950, 700)
    
    def setup_header_section(self, layout):
        """Setup the header section with title and file info."""
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 5, 10, 5)
        
        # Title label
        self.title_label = QLabel("📖 Recite")
        self.title_label.setObjectName("titleLabel")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # File info
        self.file_info_label = QLabel("No file loaded")
        self.file_info_label.setObjectName("fileInfoLabel")
        header_layout.addWidget(self.file_info_label)
        
        header_layout.addSpacing(20)
        
        # Load button
        self.load_btn = QPushButton("📂 Load")
        self.load_btn.setObjectName("loadButton")
        self.load_btn.clicked.connect(self.load_files)
        header_layout.addWidget(self.load_btn)
        
        layout.addWidget(header_frame)
    
    def create_lyrics_panel(self) -> QWidget:
        """Create the lyrics list panel."""
        panel = QGroupBox("Lyrics")
        panel.setObjectName("lyricsPanel")
        layout = QVBoxLayout(panel)
        
        self.lyrics_list = QListWidget()
        self.lyrics_list.setObjectName("lyricsList")
        self.lyrics_list.itemDoubleClicked.connect(self.on_lyric_double_clicked)
        layout.addWidget(self.lyrics_list)
        
        # Progress info
        self.progress_label = QLabel("Progress: 0 / 0")
        self.progress_label.setObjectName("progressLabel")
        layout.addWidget(self.progress_label)
        
        return panel
    
    def create_control_panel(self) -> QWidget:
        """Create the main control panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Current line display
        current_group = QGroupBox("Current Line")
        current_group.setObjectName("currentLineGroup")
        current_layout = QVBoxLayout(current_group)
        current_layout.setContentsMargins(8, 15, 8, 8)
        
        self.current_line_label = QLabel("Press 'Start' to begin")
        self.current_line_label.setObjectName("currentLineLabel")
        self.current_line_label.setWordWrap(True)
        self.current_line_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_line_label.setMinimumHeight(80)
        current_layout.addWidget(self.current_line_label)
        
        # Timestamp display
        self.timestamp_label = QLabel("")
        self.timestamp_label.setObjectName("timestampLabel")
        self.timestamp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        current_layout.addWidget(self.timestamp_label)
        
        layout.addWidget(current_group)
        
        # Playback controls
        controls_group = QGroupBox("Controls")
        controls_group.setObjectName("controlsGroup")
        controls_layout = QVBoxLayout(controls_group)
        controls_layout.setContentsMargins(8, 15, 8, 8)
        controls_layout.setSpacing(6)
        
        # Main control buttons - row 1
        btn_layout1 = QHBoxLayout()
        btn_layout1.setSpacing(4)
        
        self.start_btn = QPushButton("▶ Start")
        self.start_btn.setObjectName("startButton")
        self.start_btn.clicked.connect(self.start_recitation)
        btn_layout1.addWidget(self.start_btn)
        
        self.replay_btn = QPushButton("🔄 Replay")
        self.replay_btn.setObjectName("replayButton")
        self.replay_btn.clicked.connect(self.replay_current_line)
        self.replay_btn.setEnabled(False)
        btn_layout1.addWidget(self.replay_btn)
        
        controls_layout.addLayout(btn_layout1)
        
        # Main control buttons - row 2
        btn_layout2 = QHBoxLayout()
        btn_layout2.setSpacing(4)
        
        self.prev_btn = QPushButton("⏮ Prev")
        self.prev_btn.setObjectName("prevButton")
        self.prev_btn.clicked.connect(self.previous_line)
        self.prev_btn.setEnabled(False)
        btn_layout2.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton("⏭ Next")
        self.next_btn.setObjectName("nextButton")
        self.next_btn.clicked.connect(self.next_line)
        self.next_btn.setEnabled(False)
        btn_layout2.addWidget(self.next_btn)
        
        self.reset_btn = QPushButton("🔃 Reset")
        self.reset_btn.setObjectName("resetButton")
        self.reset_btn.clicked.connect(self.reset_recitation)
        btn_layout2.addWidget(self.reset_btn)
        
        controls_layout.addLayout(btn_layout2)
        
        layout.addWidget(controls_group)
        
        # Volume and Speed in one row
        audio_group = QGroupBox("Audio Settings")
        audio_layout = QVBoxLayout(audio_group)
        audio_layout.setContentsMargins(8, 15, 8, 8)
        audio_layout.setSpacing(6)
        
        # Volume row
        volume_layout = QHBoxLayout()
        volume_layout.setSpacing(4)
        volume_label_icon = QLabel("🔊 Vol:")
        volume_label_icon.setMinimumWidth(45)
        volume_layout.addWidget(volume_label_icon)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        initial_volume = self.settings.get('volume', 80)
        self.volume_slider.setValue(initial_volume)
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        volume_layout.addWidget(self.volume_slider)
        
        self.volume_label = QLabel(f"{initial_volume}%")
        self.volume_label.setMinimumWidth(35)
        volume_layout.addWidget(self.volume_label)
        
        audio_layout.addLayout(volume_layout)
        
        # Speed row
        speed_layout = QHBoxLayout()
        speed_layout.setSpacing(4)
        speed_label_icon = QLabel("⏩ Spd:")
        speed_label_icon.setMinimumWidth(45)
        speed_layout.addWidget(speed_label_icon)
        
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 20)  # 0.1 to 2.0, step 0.1
        initial_speed = int(self.settings.get('playback_rate', 1.0) * 10)
        self.speed_slider.setValue(initial_speed)
        self.speed_slider.valueChanged.connect(self.on_speed_changed)
        speed_layout.addWidget(self.speed_slider)
        
        self.speed_label = QLabel(f"{self.settings.get('playback_rate', 1.0):.1f}x")
        self.speed_label.setMinimumWidth(35)
        speed_layout.addWidget(self.speed_label)
        
        # Save button
        self.save_speed_btn = QPushButton("💾")
        self.save_speed_btn.setObjectName("saveSpeedButton")
        self.save_speed_btn.clicked.connect(self.save_settings)
        self.save_speed_btn.setToolTip("Save settings")
        self.save_speed_btn.setFixedWidth(35)
        speed_layout.addWidget(self.save_speed_btn)
        
        audio_layout.addLayout(speed_layout)
        
        layout.addWidget(audio_group)
        
        # Instructions (collapsible/smaller)
        instructions_group = QGroupBox("Help")
        instructions_layout = QVBoxLayout(instructions_group)
        instructions_layout.setContentsMargins(8, 15, 8, 8)
        
        instructions_text = QLabel(
            "Space: Start/Next | R: Replay | ←→: Prev/Next | Esc: Reset"
        )
        instructions_text.setObjectName("instructionsLabel")
        instructions_text.setWordWrap(True)
        instructions_layout.addWidget(instructions_text)
        
        layout.addWidget(instructions_group)
        
        layout.addStretch()
        
        return panel
    
    def setup_bottom_controls(self, layout):
        """Setup the bottom progress bar and status."""
        bottom_frame = QFrame()
        bottom_frame.setObjectName("bottomFrame")
        bottom_layout = QVBoxLayout(bottom_frame)
        
        # Progress bar
        progress_layout = QHBoxLayout()
        self.position_label = QLabel("00:00")
        progress_layout.addWidget(self.position_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setTextVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.duration_label = QLabel("00:00")
        progress_layout.addWidget(self.duration_label)
        
        bottom_layout.addLayout(progress_layout)
        
        # Status bar
        self.status_label = QLabel("Ready - Load files to begin")
        self.status_label.setObjectName("statusLabel")
        bottom_layout.addWidget(self.status_label)
        
        layout.addWidget(bottom_frame)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Space - Play/Next
        space_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        space_shortcut.activated.connect(self.on_space_pressed)
        
        # R - Replay
        replay_shortcut = QShortcut(QKeySequence(Qt.Key.Key_R), self)
        replay_shortcut.activated.connect(self.replay_current_line)
        
        # Left arrow - Previous
        prev_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        prev_shortcut.activated.connect(self.previous_line)
        
        # Right arrow - Next
        next_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        next_shortcut.activated.connect(self.next_line)
        
        # Escape - Reset
        reset_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        reset_shortcut.activated.connect(self.reset_recitation)
    
    def apply_styles(self):
        """Apply CSS styles to the application."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e2e;
            }
            
            QWidget {
                color: #cdd6f4;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
            
            #headerFrame {
                background-color: #313244;
                border-radius: 8px;
                padding: 5px;
            }
            
            #titleLabel {
                font-size: 18px;
                font-weight: bold;
                color: #89b4fa;
            }
            
            #fileInfoLabel {
                font-size: 11px;
                color: #a6adc8;
            }
            
            #loadButton {
                background-color: #89b4fa;
                color: #1e1e2e;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 12px;
            }
            
            #loadButton:hover {
                background-color: #b4befe;
            }
            
            QGroupBox {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: bold;
                font-size: 11px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
                color: #89b4fa;
            }
            
            #lyricsList {
                background-color: #1e1e2e;
                border: 1px solid #45475a;
                border-radius: 4px;
                padding: 3px;
                font-size: 12px;
            }
            
            #lyricsList::item {
                padding: 5px;
                border-radius: 2px;
            }
            
            #lyricsList::item:selected {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            
            #lyricsList::item:hover {
                background-color: #45475a;
            }
            
            #currentLineLabel {
                font-size: 16px;
                font-weight: bold;
                color: #f5e0dc;
                background-color: #1e1e2e;
                border: 2px solid #89b4fa;
                border-radius: 8px;
                padding: 15px;
            }
            
            #timestampLabel {
                font-size: 12px;
                color: #a6adc8;
            }
            
            #instructionsLabel {
                font-size: 11px;
                color: #bac2de;
            }
            
            #progressLabel {
                font-size: 11px;
                color: #a6adc8;
                padding: 3px;
            }
            
            QPushButton {
                background-color: #45475a;
                color: #cdd6f4;
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #585b70;
            }
            
            QPushButton:pressed {
                background-color: #313244;
            }
            
            QPushButton:disabled {
                background-color: #313244;
                color: #6c7086;
            }
            
            #startButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
            }
            
            #startButton:hover {
                background-color: #94e2d5;
            }
            
            #replayButton {
                background-color: #f9e2af;
                color: #1e1e2e;
            }
            
            #replayButton:hover {
                background-color: #f5c2e7;
            }
            
            #nextButton {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
            
            #nextButton:hover {
                background-color: #b4befe;
            }
            
            #prevButton {
                background-color: #cba6f7;
                color: #1e1e2e;
            }
            
            #prevButton:hover {
                background-color: #f5c2e7;
            }
            
            #resetButton {
                background-color: #f38ba8;
                color: #1e1e2e;
            }
            
            #resetButton:hover {
                background-color: #eba0ac;
            }
            
            #saveSpeedButton {
                background-color: #94e2d5;
                color: #1e1e2e;
                padding: 6px 8px;
                font-size: 11px;
            }
            
            #saveSpeedButton:hover {
                background-color: #a6e3a1;
            }
            
            QSlider::groove:horizontal {
                border: 1px solid #45475a;
                height: 6px;
                background: #313244;
                border-radius: 3px;
            }
            
            QSlider::handle:horizontal {
                background: #89b4fa;
                border: none;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            
            QSlider::sub-page:horizontal {
                background: #89b4fa;
                border-radius: 3px;
            }
            
            #bottomFrame {
                background-color: #313244;
                border-radius: 8px;
                padding: 6px;
            }
            
            #progressBar {
                background-color: #1e1e2e;
                border: 1px solid #45475a;
                border-radius: 4px;
                height: 8px;
            }
            
            #progressBar::chunk {
                background-color: #89b4fa;
                border-radius: 3px;
            }
            
            #statusLabel {
                font-size: 11px;
                color: #a6adc8;
                padding: 3px;
            }
            
            QSplitter::handle {
                background-color: #45475a;
                width: 2px;
            }
        """)
    
    def load_files(self):
        """Open file dialog to load LRC or MP3 files. User can select either file type first."""
        # Get the Recite folder path as default
        script_dir = Path(__file__).parent
        
        # Open file dialog that accepts both LRC and MP3 files
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select LRC or MP3 File",
            str(script_dir),
            "Media Files (*.lrc *.mp3);;LRC Files (*.lrc);;MP3 Files (*.mp3);;All Files (*.*)"
        )
        
        if not file_path:
            return
        
        selected_file = Path(file_path)
        
        if selected_file.suffix.lower() == '.lrc':
            # User selected LRC file, try to find matching MP3
            self.load_lrc_file(file_path)
            mp3_path = selected_file.with_suffix('.mp3')
            
            if mp3_path.exists():
                self.load_audio_file(str(mp3_path))
            else:
                # Ask user to select MP3 file
                mp3_file, _ = QFileDialog.getOpenFileName(
                    self,
                    "Select MP3 File",
                    str(selected_file.parent),
                    "MP3 Files (*.mp3);;Audio Files (*.mp3 *.wav *.ogg);;All Files (*.*)"
                )
                if mp3_file:
                    self.load_audio_file(mp3_file)
                    
        elif selected_file.suffix.lower() == '.mp3':
            # User selected MP3 file, try to find matching LRC
            self.load_audio_file(file_path)
            lrc_path = selected_file.with_suffix('.lrc')
            
            if lrc_path.exists():
                self.load_lrc_file(str(lrc_path))
            else:
                # Ask user to select LRC file
                lrc_file, _ = QFileDialog.getOpenFileName(
                    self,
                    "Select LRC File",
                    str(selected_file.parent),
                    "LRC Files (*.lrc);;All Files (*.*)"
                )
                if lrc_file:
                    self.load_lrc_file(lrc_file)
        else:
            QMessageBox.warning(self, "Warning", "Please select an LRC or MP3 file.")
    
    def load_lrc_file(self, filepath: str):
        """Load and parse an LRC file."""
        try:
            self.metadata, self.lyrics = self.lrc_parser.parse_file(filepath)
            self.lrc_file = filepath
            
            # Update lyrics list
            self.lyrics_list.clear()
            for i, lyric in enumerate(self.lyrics):
                item = QListWidgetItem(f"{lyric.timestamp_str} {lyric.text}")
                self.lyrics_list.addItem(item)
            
            # Update UI
            title = self.metadata.get('ti', Path(filepath).stem)
            self.title_label.setText(f"📖 {title}")
            self.file_info_label.setText(f"LRC: {Path(filepath).name}")
            self.progress_label.setText(f"Progress: 0 / {len(self.lyrics)}")
            self.status_label.setText(f"Loaded {len(self.lyrics)} lines from LRC file")
            
            # Reset state
            self.current_line_index = -1
            self.update_button_states()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load LRC file:\n{str(e)}")
    
    def load_audio_file(self, filepath: str):
        """Load an audio file."""
        try:
            self.audio_file = filepath
            self.media_player.setSource(QUrl.fromLocalFile(filepath))
            
            # Update file info
            current_text = self.file_info_label.text()
            self.file_info_label.setText(f"{current_text} | MP3: {Path(filepath).name}")
            self.status_label.setText("Files loaded - Press Start to begin")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load audio file:\n{str(e)}")
    
    def start_recitation(self):
        """Start or resume the recitation."""
        if not self.lyrics:
            QMessageBox.warning(self, "Warning", "Please load files first!")
            return
        
        if self.current_line_index < 0:
            self.current_line_index = 0
        
        self.play_current_line()
    
    def play_current_line(self):
        """Play the audio for the current line."""
        if self.current_line_index < 0 or self.current_line_index >= len(self.lyrics):
            return
        
        current_lyric = self.lyrics[self.current_line_index]
        
        # Update display
        self.current_line_label.setText(current_lyric.text)
        self.timestamp_label.setText(current_lyric.timestamp_str)
        
        # Highlight in list
        self.lyrics_list.setCurrentRow(self.current_line_index)
        
        # Update progress
        self.progress_label.setText(f"Progress: {self.current_line_index + 1} / {len(self.lyrics)}")
        
        # Calculate end position
        start_ms = current_lyric.timestamp_ms
        if self.current_line_index + 1 < len(self.lyrics):
            end_ms = self.lyrics[self.current_line_index + 1].timestamp_ms
        else:
            end_ms = self.media_player.duration() if self.media_player.duration() > 0 else start_ms + 5000
        
        self.target_end_ms = end_ms
        
        # Set position and play
        self.media_player.setPosition(start_ms)
        self.media_player.play()
        self.is_playing = True
        
        # Start position timer
        self.position_timer.start(50)
        
        # Update button states
        self.update_button_states()
        self.status_label.setText(f"Playing line {self.current_line_index + 1}... Listen and prepare to recite!")
    
    def check_playback_position(self):
        """Check if playback has reached the end of current line."""
        if not self.is_playing:
            return
        
        current_pos = self.media_player.position()
        
        if current_pos >= self.target_end_ms - 50:  # Small buffer
            self.media_player.pause()
            self.is_playing = False
            self.position_timer.stop()
            self.status_label.setText("Your turn! Recite the line, then press Space or Next to continue")
            self.update_button_states()
    
    def replay_current_line(self):
        """Replay the current line."""
        if self.current_line_index >= 0:
            self.play_current_line()
    
    def next_line(self):
        """Move to the next line."""
        if self.current_line_index < len(self.lyrics) - 1:
            self.current_line_index += 1
            self.play_current_line()
        else:
            self.status_label.setText("🎉 Congratulations! You've completed all lines!")
            self.current_line_label.setText("✅ Recitation Complete!")
            self.media_player.stop()
            self.is_playing = False
    
    def previous_line(self):
        """Move to the previous line."""
        if self.current_line_index > 0:
            self.current_line_index -= 1
            self.play_current_line()
    
    def reset_recitation(self):
        """Reset the recitation to the beginning."""
        self.media_player.stop()
        self.is_playing = False
        self.current_line_index = -1
        self.position_timer.stop()
        
        self.current_line_label.setText("Press 'Start' to begin")
        self.timestamp_label.setText("")
        self.lyrics_list.clearSelection()
        self.progress_label.setText(f"Progress: 0 / {len(self.lyrics)}")
        self.status_label.setText("Reset - Press Start to begin again")
        
        self.update_button_states()
    
    def on_space_pressed(self):
        """Handle space key press."""
        if self.current_line_index < 0:
            self.start_recitation()
        elif not self.is_playing:
            self.next_line()
    
    def on_lyric_double_clicked(self, item):
        """Handle double-click on a lyric line."""
        row = self.lyrics_list.row(item)
        self.current_line_index = row
        self.play_current_line()
    
    def on_volume_changed(self, value):
        """Handle volume slider change."""
        self.audio_output.setVolume(value / 100.0)
        self.volume_label.setText(f"{value}%")
    
    def on_position_changed(self, position):
        """Handle media player position change."""
        self.position_label.setText(self.format_time(position))
        if self.media_player.duration() > 0:
            self.progress_bar.setValue(int(position * 100 / self.media_player.duration()))
    
    def on_duration_changed(self, duration):
        """Handle media player duration change."""
        self.duration_label.setText(self.format_time(duration))
        self.progress_bar.setMaximum(100)
    
    def on_playback_state_changed(self, state):
        """Handle playback state changes."""
        pass  # Handled by position timer
    
    def update_button_states(self):
        """Update button enabled states based on current state."""
        has_lyrics = len(self.lyrics) > 0
        has_started = self.current_line_index >= 0
        
        self.start_btn.setEnabled(has_lyrics)
        self.replay_btn.setEnabled(has_started and not self.is_playing)
        self.next_btn.setEnabled(has_started and not self.is_playing and self.current_line_index < len(self.lyrics) - 1)
        self.prev_btn.setEnabled(has_started and not self.is_playing and self.current_line_index > 0)
        self.reset_btn.setEnabled(has_started)
        
        # Update start button text
        if has_started:
            self.start_btn.setText("▶ Continue")
        else:
            self.start_btn.setText("▶ Start")
    
    @staticmethod
    def format_time(ms: int) -> str:
        """Format milliseconds to MM:SS string."""
        seconds = ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def load_settings(self) -> dict:
        """Load settings from JSON file."""
        default_settings = {
            'playback_rate': 1.0,
            'volume': 80
        }
        
        try:
            if self.SETTINGS_FILE.exists():
                with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    return {**default_settings, **settings}
        except Exception as e:
            print(f"Error loading settings: {e}")
        
        return default_settings
    
    def save_settings(self):
        """Save current settings to JSON file."""
        try:
            settings = {
                'playback_rate': self.playback_rate,
                'volume': self.volume_slider.value()
            }
            
            with open(self.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
            
            self.status_label.setText(f"✅ Settings saved (Speed: {self.playback_rate:.1f}x, Volume: {settings['volume']}%)")
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to save settings:\n{str(e)}")
    
    def on_speed_changed(self, value):
        """Handle playback speed slider change."""
        # Convert slider value (1-20) to playback rate (0.1-2.0)
        self.playback_rate = value / 10.0
        self.speed_label.setText(f"{self.playback_rate:.1f}x")
        self.media_player.setPlaybackRate(self.playback_rate)
    
    def closeEvent(self, event):
        """Handle window close event."""
        self.media_player.stop()
        self.position_timer.stop()
        event.accept()


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("Recite")
    app.setApplicationDisplayName("Recite - Text Recitation Practice")
    
    window = ReciteMainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
