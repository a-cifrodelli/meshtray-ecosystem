import os
import hashlib
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QColor, QImage, QPainter
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QLineEdit, QPushButton, QFrame, QSizePolicy,
    QListWidget, QComboBox, QTextEdit, QMessageBox, QListWidgetItem
)
from config import *

# ─────────────────────────────────────────────────────────────
#  Identicon Generator (Gitea-like geometric patterns in memory)
# ─────────────────────────────────────────────────────────────
def get_identicon(name, size=128):
    h = hashlib.sha256(name.encode("utf-8")).digest()
    
    # Colore casuale basato sull'hash (HSV)
    hue = ((h[0] << 8) | h[1]) % 360
    color = QColor.fromHsv(hue, 150, 210) # Tonalità pastello piacevole
    
    # Immagine di sfondo grigio chiaro (stile Gitea)
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(QColor("#f1f5f9"))
    
    painter = QPainter(img)
    painter.setPen(Qt.PenStyle.NoPen)
    
    margin = size // 10
    grid_size = size - 2 * margin
    cell_size = grid_size // 5
    
    # Griglia 5x5 simmetrica
    active = [[False]*5 for _ in range(5)]
    byte_idx = 2
    bit_idx = 0
    
    for row in range(5):
        for col in range(3):
            byte_val = h[byte_idx]
            is_active = ((byte_val >> bit_idx) & 1) == 1
            active[row][col] = is_active
            active[row][4 - col] = is_active
            
            bit_idx += 1
            if bit_idx >= 8:
                bit_idx = 0
                byte_idx += 1
                
    # Disegna le celle attive
    for row in range(5):
        for col in range(5):
            if active[row][col]:
                x = margin + col * cell_size
                y = margin + row * cell_size
                painter.fillRect(x, y, cell_size, cell_size, color)
                
    painter.end()
    return img

# ─────────────────────────────────────────────────────────────
#  QSS Stylesheet (Modern Dark-Blue theme)
# ─────────────────────────────────────────────────────────────
THEME_QSS = """
QWidget {
    background-color: #121826;
    color: #ffffff;
    font-family: "Segoe UI", Arial, sans-serif;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    border: none;
    background: #121826;
    width: 8px;
}
QScrollBar::handle:vertical {
    background: #28334e;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #00f2fe;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

QLineEdit {
    background-color: #182030;
    border: 1px solid #28334e;
    border-radius: 6px;
    padding: 6px 12px;
    color: #ffffff;
    font-size: 13px;
}
QLineEdit:focus {
    border: 1px solid #00f2fe;
}

QPushButton {
    background-color: #1c2333;
    border: 1px solid #28334e;
    border-radius: 6px;
    padding: 6px 16px;
    color: #ffffff;
    font-size: 13px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #28334e;
    border: 1px solid #00f2fe;
}
QPushButton:pressed {
    background-color: #121826;
}
"""

CARD_QSS = """
QFrame#MessageCard {
    background-color: #1c2333;
    border: 1px solid #28334e;
    border-radius: 8px;
}
QFrame#MessageCard QLabel {
    background-color: transparent;
    border: none;
}
QFrame#MessageCard QFrame#Separator {
    background-color: #28334e;
    max-height: 1px;
}
"""

# ─────────────────────────────────────────────────────────────
#  Component: MessageCard (Scheda messaggio)
# ─────────────────────────────────────────────────────────────
class MessageCard(QFrame):
    reply_clicked = pyqtSignal(str)     # Emits sender node_id
    channel_clicked = pyqtSignal(str)   # Emits channel name

    def __init__(self, ts, from_node, to_node, channel, text, parent=None):
        super().__init__(parent)
        self.setObjectName("MessageCard")
        self.setStyleSheet(CARD_QSS)
        self.text = text
        self.from_node = from_node
        self.to_node = to_node
        self.channel = channel

        # Main horizontal layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(12)

        # Avatar Label (Identicon generated from from_node)
        self.avatar_lbl = QLabel()
        self.avatar_lbl.setFixedSize(40, 40)
        img = get_identicon(from_node, 40)
        self.avatar_lbl.setPixmap(QPixmap.fromImage(img))
        self.avatar_lbl.setStyleSheet("border-radius: 4px; border: 1px solid #1c2333; background-color: transparent;")
        main_layout.addWidget(self.avatar_lbl, alignment=Qt.AlignmentFlag.AlignTop)

        # Content column (Vertical)
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Header: From -> To | Channel | Time
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        from_lbl = QLabel(f"📡  {from_node}")
        from_lbl.setStyleSheet("font-weight: bold; color: #00f2fe;")
        header.addWidget(from_lbl)

        arrow_lbl = QLabel("  ➡  ")
        arrow_lbl.setStyleSheet("color: #8a9ab0;")
        header.addWidget(arrow_lbl)

        to_lbl = QLabel(to_node)
        to_lbl.setStyleSheet("font-weight: bold; color: #3b82f6;")
        header.addWidget(to_lbl)

        if channel:
            self.chan_btn = QPushButton(channel)
            self.chan_btn.setStyleSheet("""
                background-color: #f59e0b;
                color: #121826;
                font-weight: bold;
                border-radius: 4px;
                font-size: 10px;
                border: none;
                padding: 2px 6px;
            """)
            self.chan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.chan_btn.clicked.connect(lambda: self.channel_clicked.emit(self.channel))
            header.addWidget(self.chan_btn)

        header.addStretch()

        if from_node != "local_node":
            self.reply_btn = QPushButton("💬 Rispondi")
            self.reply_btn.setStyleSheet("""
                font-size: 10px;
                padding: 2px 8px;
                background-color: #182030;
                border: 1px solid #28334e;
                border-radius: 4px;
                font-weight: normal;
                margin-right: 8px;
            """)
            self.reply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.reply_btn.clicked.connect(lambda: self.reply_clicked.emit(self.from_node))
            header.addWidget(self.reply_btn)

        time_lbl = QLabel(ts)
        time_lbl.setStyleSheet("color: #8a9ab0; font-size: 11px;")
        header.addWidget(time_lbl)

        content_layout.addLayout(header)

        # Separator line
        sep = QFrame()
        sep.setObjectName("Separator")
        content_layout.addWidget(sep)

        # Message Text
        body_lbl = QLabel(text)
        body_lbl.setWordWrap(True)
        body_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body_lbl.setStyleSheet("font-size: 13px; line-height: 1.4; color: #e2e8f0; margin-top: 4px;")
        content_layout.addWidget(body_lbl)

        main_layout.addLayout(content_layout)

# ─────────────────────────────────────────────────────────────
#  Component: Header Panel
# ─────────────────────────────────────────────────────────────
class HeaderPanel(QFrame):
    def __init__(self, title, subtitle, show_badge=False, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #0d121d; border-bottom: 1px solid #1c2333;")
        self.setFixedHeight(70)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 10, 18, 10)

        # Text column
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; background-color: transparent;")
        text_layout.addWidget(self.title_lbl)

        self.sub_lbl = QLabel(subtitle)
        self.sub_lbl.setStyleSheet("font-size: 11px; color: #8a9ab0; background-color: transparent;")
        text_layout.addWidget(self.sub_lbl)

        layout.addLayout(text_layout)
        layout.addStretch()

        self.badge_lbl = None
        if show_badge:
            self.badge_lbl = QLabel("● IN CONNESSIONE...")
            self.badge_lbl.setStyleSheet("color: #94a3b8; font-weight: bold; font-size: 12px; background-color: transparent; padding-right: 4px;")
            layout.addWidget(self.badge_lbl)

    def set_connected(self, connected, is_mock=False, radio_online=False):
        if self.badge_lbl:
            if is_mock:
                self.badge_lbl.setText("● MOCK")
                self.badge_lbl.setStyleSheet("color: #3b82f6; font-weight: bold; font-size: 12px; background-color: transparent;")
            elif connected:
                if radio_online:
                    self.badge_lbl.setText("● LIVE · 📻 RADIO ONLINE")
                    self.badge_lbl.setStyleSheet("color: #00ff87; font-weight: bold; font-size: 12px; background-color: transparent;")
                else:
                    self.badge_lbl.setText("● LIVE · 📻 RADIO OFFLINE")
                    self.badge_lbl.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 12px; background-color: transparent;")
            else:
                self.badge_lbl.setText("● DISCONNESSO")
                self.badge_lbl.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 12px; background-color: transparent;")

# ─────────────────────────────────────────────────────────────
#  Component: MetricCard
# ─────────────────────────────────────────────────────────────
class MetricCard(QFrame):
    def __init__(self, title, initial_value, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #1c2333; border: 1px solid #28334e; border-radius: 8px;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #8a9ab0; font-size: 10px; background-color: transparent; text-transform: uppercase;")
        layout.addWidget(title_lbl)

        self.val_lbl = QLabel(initial_value)
        self.val_lbl.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold; background-color: transparent;")
        layout.addWidget(self.val_lbl)

    def set_value(self, value):
        self.val_lbl.setText(str(value))

# ─────────────────────────────────────────────────────────────
#  MainWindow: Ultimi Messaggi
# ─────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    node_selected = pyqtSignal(str)
    channel_selected = pyqtSignal(str)
    reply_triggered = pyqtSignal(str)         # Emits node_id
    channel_reply_triggered = pyqtSignal(str) # Emits channel name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Meshtray – Ultimi Messaggi")
        self.resize(1000, 720) # Made wider for the sidebar
        self.setMinimumSize(700, 450)
        self.setStyleSheet(THEME_QSS)

        self.is_connected = False
        self.is_mock = False
        self.radio_online = False

        # Icona finestra
        if os.path.exists(FAVICON_PNG):
            self.setWindowIcon(QIcon(FAVICON_PNG))

        # Main Widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Header
        self.header = HeaderPanel("Meshtray", "Meshtray Ecosystem · messaggi live dalla mesh", show_badge=True)
        main_layout.addWidget(self.header)

        # Horizontal Split layout for feed and sidebar
        content = QWidget()
        h_layout = QHBoxLayout(content)
        h_layout.setContentsMargins(12, 12, 12, 12)
        h_layout.setSpacing(12)

        # Left pane (Stats + Scroll area)
        left_pane = QWidget()
        left_layout = QVBoxLayout(left_pane)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # 2. Stats row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(8)
        self.stat_count = MetricCard("MESSAGGI RICEVUTI", "0")
        self.stat_last = MetricCard("ULTIMO MESSAGGIO", "—")
        stats_layout.addWidget(self.stat_count)
        stats_layout.addWidget(self.stat_last)
        left_layout.addLayout(stats_layout)

        # 3. Scroll area and feed list
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        
        self.feed_widget = QWidget()
        self.feed_widget.setStyleSheet("background-color: transparent;")
        self.feed_layout = QVBoxLayout(self.feed_widget)
        self.feed_layout.setContentsMargins(0, 0, 0, 0)
        self.feed_layout.setSpacing(8)
        self.feed_layout.addStretch()  # Spinge i messaggi in alto
        
        self.scroll.setWidget(self.feed_widget)
        left_layout.addWidget(self.scroll)
        
        h_layout.addWidget(left_pane, 3)

        # Right pane (Sidebar)
        self.sidebar = QWidget()
        self.sidebar.setStyleSheet("background-color: #0d121d; border-left: 1px solid #1c2333;")
        self.sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 0, 10, 0)
        sidebar_layout.setSpacing(8)

        nodes_lbl = QLabel("📡 NODI ATTIVI")
        nodes_lbl.setStyleSheet("color: #00f2fe; font-size: 11px; font-weight: bold; margin-top: 5px;")
        sidebar_layout.addWidget(nodes_lbl)

        self.nodes_list = QListWidget()
        self.nodes_list.setStyleSheet("background-color: #121826; border: 1px solid #1c2333; border-radius: 4px; color: #ffffff;")
        self.nodes_list.itemClicked.connect(self.on_sidebar_node_clicked)
        sidebar_layout.addWidget(self.nodes_list, 2)

        chans_lbl = QLabel("💬 CANALI RILEVATI")
        chans_lbl.setStyleSheet("color: #f59e0b; font-size: 11px; font-weight: bold; margin-top: 8px;")
        sidebar_layout.addWidget(chans_lbl)

        self.channels_list = QListWidget()
        self.channels_list.setStyleSheet("background-color: #121826; border: 1px solid #1c2333; border-radius: 4px; color: #ffffff;")
        self.channels_list.itemClicked.connect(self.on_sidebar_channel_clicked)
        sidebar_layout.addWidget(self.channels_list, 1)

        h_layout.addWidget(self.sidebar, 1)
        main_layout.addWidget(content)

        self.messages_count = 0
        self.cards = []

    def on_sidebar_node_clicked(self, item):
        self.node_selected.emit(item.text())

    def on_sidebar_channel_clicked(self, item):
        self.channel_selected.emit(item.text())

    def update_sidebar(self, nodes, channels, radio_online=False):
        self.radio_online = radio_online
        self.nodes_list.clear()
        if nodes:
            for node in nodes:
                self.nodes_list.addItem(node)
        else:
            item = QListWidgetItem("Nessun nodo attivo" if radio_online else "📻 Radio offline")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.nodes_list.addItem(item)

        self.channels_list.clear()
        if channels:
            for chan in channels:
                self.channels_list.addItem(chan)
        else:
            item = QListWidgetItem("Nessun canale" if radio_online else "📻 Radio offline")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.channels_list.addItem(item)

        self.set_connected(self.is_connected, self.is_mock, radio_online)

    def add_message(self, ts, from_node, to_node, channel, text):
        card = MessageCard(ts, from_node, to_node, channel, text)
        card.reply_clicked.connect(self.reply_triggered)
        card.channel_clicked.connect(self.channel_reply_triggered)
        
        # Inserisce sopra lo stretch (quindi in coda ma spinto in alto)
        self.feed_layout.insertWidget(self.feed_layout.count() - 1, card)
        self.cards.append(card)
        self.messages_count += 1
        
        # Limita la memoria al massimo dei messaggi
        if len(self.cards) > MAX_MESSAGES:
            oldest = self.cards.pop(0)
            self.feed_layout.removeWidget(oldest)
            oldest.deleteLater()
            self.messages_count -= 1

        self.stat_count.set_value(self.messages_count)
        self.stat_last.set_value(ts)

        # Auto-scroll verso il fondo
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def set_connected(self, connected, is_mock=False, radio_online=None):
        self.is_connected = connected
        self.is_mock = is_mock
        if radio_online is not None:
            self.radio_online = radio_online
        self.header.set_connected(connected, is_mock, self.radio_online)

    def closeEvent(self, event):
        # Invece di chiudere l'app, nasconde la finestra per rimanere nel tray
        event.ignore()
        self.hide()

# ─────────────────────────────────────────────────────────────
#  ArchiveWindow: Archivio Storico
# ─────────────────────────────────────────────────────────────
class ArchiveWindow(QMainWindow):
    reply_triggered = pyqtSignal(str)
    channel_reply_triggered = pyqtSignal(str)

    def __init__(self, connection_thread, parent=None):
        super().__init__(parent)
        self.conn = connection_thread
        self.setWindowTitle("Meshtray – Archivio Messaggi")
        self.resize(800, 760)
        self.setMinimumSize(500, 450)
        self.setStyleSheet(THEME_QSS)

        if os.path.exists(FAVICON_PNG):
            self.setWindowIcon(QIcon(FAVICON_PNG))

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Header
        self.header = HeaderPanel("Meshtray", "Meshtray Ecosystem · storico messaggi dal database")
        main_layout.addWidget(self.header)

        # Content Widget
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(12)

        # 2. Search bar
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Filtra messaggi per testo, mittente o canale...")
        self.search_input.textChanged.connect(self.filter_cards)
        search_layout.addWidget(self.search_input)

        self.clear_btn = QPushButton("✕")
        self.clear_btn.setFixedWidth(40)
        self.clear_btn.clicked.connect(lambda: self.search_input.clear())
        search_layout.addWidget(self.clear_btn)
        content_layout.addLayout(search_layout)

        # 3. Feed list scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        
        self.feed_widget = QWidget()
        self.feed_widget.setStyleSheet("background-color: transparent;")
        self.feed_layout = QVBoxLayout(self.feed_widget)
        self.feed_layout.setContentsMargins(0, 0, 0, 0)
        self.feed_layout.setSpacing(8)
        self.feed_layout.addStretch()
        
        self.scroll.setWidget(self.feed_widget)
        content_layout.addWidget(self.scroll)

        # 4. Footer Separator
        sep = QFrame()
        sep.setStyleSheet("background-color: #1c2333; max-height: 1px;")
        content_layout.addWidget(sep)

        # 5. Bottom toolbar
        footer_layout = QHBoxLayout()
        self.load_btn = QPushButton("⬇  Carica altri")
        self.load_btn.clicked.connect(self.load_more)
        footer_layout.addWidget(self.load_btn)

        self.reload_btn = QPushButton("🔄  Ricarica dall'inizio")
        self.reload_btn.clicked.connect(self.reload_archive)
        self.reload_btn.setStyleSheet("background-color: transparent; border: 1px solid #8a9ab0;")
        footer_layout.addWidget(self.reload_btn)
        footer_layout.addStretch()

        content_layout.addLayout(footer_layout)
        main_layout.addWidget(content)

        self.offset = 0
        self.cards = []

        # Hook di connessione segnali
        self.conn.archive_message_received.connect(self.add_archive_message)
        self.conn.archive_load_finished.connect(self.on_load_finished)

    def showEvent(self, event):
        super().showEvent(event)
        if self.offset == 0 and not self.cards:
            self.load_more()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def add_archive_message(self, ts, from_node, to_node, channel, text):
        card = MessageCard(ts, from_node, to_node, channel, text)
        card.reply_clicked.connect(self.reply_triggered)
        card.channel_clicked.connect(self.channel_reply_triggered)
        self.feed_layout.insertWidget(self.feed_layout.count() - 1, card)
        self.cards.append(card)
        self.offset += 1

        # Applica subito il filtro se c'è testo inserito
        query = self.search_input.text().lower().strip()
        if query:
            match = any(query in str(x).lower() for x in [text, from_node, to_node, channel])
            card.setVisible(match)

    def load_more(self):
        self.load_btn.setEnabled(False)
        self.load_btn.setText("Caricamento...")
        self.conn.request_archive_page(self.offset, ARCHIVE_PAGE_SIZE)

    def on_load_finished(self, is_last):
        self.load_btn.setText("⬇  Carica altri")
        self.load_btn.setEnabled(not is_last)

    def reload_archive(self):
        # Pulisce tutto
        for card in self.cards:
            self.feed_layout.removeWidget(card)
            card.deleteLater()
        self.cards.clear()
        self.offset = 0
        self.load_btn.setEnabled(True)
        self.search_input.clear()
        self.load_more()

    def filter_cards(self, query):
        query = query.lower().strip()
        for card in self.cards:
            if not query:
                card.show()
            else:
                match = any(query in str(x).lower() for x in [card.text, card.from_node, card.to_node, card.channel])
                card.setVisible(match)

# ─────────────────────────────────────────────────────────────
class ChatBubble(QFrame):
    def __init__(self, ts, from_node, text, is_outgoing=False, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")

        # Outer horizontal layout
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 4, 0, 4)
        outer_layout.setSpacing(8)

        # Create the inner bubble frame
        bubble_frame = QFrame()
        bubble_layout = QVBoxLayout(bubble_frame)
        bubble_layout.setContentsMargins(10, 8, 10, 8)
        bubble_layout.setSpacing(2)

        # Style the inner bubble frame
        if is_outgoing:
            bubble_frame.setStyleSheet("""
                QFrame {
                    background-color: #1e3a8a;
                    border: 1px solid #3b82f6;
                    border-top-right-radius: 0px;
                    border-top-left-radius: 12px;
                    border-bottom-left-radius: 12px;
                    border-bottom-right-radius: 12px;
                }
            """)
        else:
            bubble_frame.setStyleSheet("""
                QFrame {
                    background-color: #1e293b;
                    border: 1px solid #334155;
                    border-top-left-radius: 0px;
                    border-top-right-radius: 12px;
                    border-bottom-left-radius: 12px;
                    border-bottom-right-radius: 12px;
                }
            """)

        # Meta info row
        meta_layout = QHBoxLayout()
        meta_layout.setContentsMargins(0, 0, 0, 0)
        
        sender_lbl = QLabel(f"📡 {from_node}" if not is_outgoing else "Me")
        sender_lbl.setStyleSheet("font-size: 10px; font-weight: bold; color: #94a3b8; background-color: transparent; border: none;")
        meta_layout.addWidget(sender_lbl)
        
        meta_layout.addStretch()
        
        time_lbl = QLabel(ts)
        time_lbl.setStyleSheet("font-size: 9px; color: #64748b; background-color: transparent; border: none;")
        meta_layout.addWidget(time_lbl)
        
        bubble_layout.addLayout(meta_layout)

        # Message body
        txt_lbl = QLabel(text)
        txt_lbl.setWordWrap(True)
        txt_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        txt_lbl.setStyleSheet("font-size: 12px; line-height: 1.3; color: #f1f5f9; background-color: transparent; border: none;")
        bubble_layout.addWidget(txt_lbl)

        # Avatar Label
        avatar_lbl = QLabel()
        avatar_lbl.setFixedSize(32, 32)
        avatar_name = "local_node" if is_outgoing else from_node
        img = get_identicon(avatar_name, 32)
        avatar_lbl.setPixmap(QPixmap.fromImage(img))
        avatar_lbl.setStyleSheet("border-radius: 4px; border: 1px solid #1c2333;")

        # Layout depending on direction
        if is_outgoing:
            outer_layout.addStretch()
            outer_layout.addWidget(bubble_frame)
            outer_layout.addWidget(avatar_lbl, alignment=Qt.AlignmentFlag.AlignBottom)
        else:
            outer_layout.addWidget(avatar_lbl, alignment=Qt.AlignmentFlag.AlignBottom)
            outer_layout.addWidget(bubble_frame)
            outer_layout.addStretch()

        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)


# ─────────────────────────────────────────────────────────────
#  ChatWindow: Finestra di Chat Dedicata
# ─────────────────────────────────────────────────────────────
class ChatWindow(QMainWindow):
    def __init__(self, connection_thread, parent=None):
        super().__init__(parent)
        self.conn = connection_thread
        self.setWindowTitle("Meshtray – Chat")
        self.resize(550, 650)
        self.setMinimumSize(400, 450)
        self.setStyleSheet(THEME_QSS)

        if os.path.exists(FAVICON_PNG):
            self.setWindowIcon(QIcon(FAVICON_PNG))

        self.target_node = None
        self.target_channel = None
        self.offset = 0
        self.known_nodes = []
        self.known_channels = []

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Header
        self.header = HeaderPanel("Nuova Chat", "Seleziona un destinatario o un canale per iniziare")
        main_layout.addWidget(self.header)

        # Content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(10)

        # 2. Target Selector (dropdowns)
        self.selector_widget = QWidget()
        sel_layout = QHBoxLayout(self.selector_widget)
        sel_layout.setContentsMargins(0, 0, 0, 0)
        sel_layout.setSpacing(6)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Privata (DM)", "Canale (Broadcast)"])
        self.type_combo.currentIndexChanged.connect(self.on_selector_type_changed)
        sel_layout.addWidget(self.type_combo)

        self.dest_combo = QComboBox()
        self.dest_combo.setEditable(True)
        self.dest_combo.setPlaceholderText("Seleziona o scrivi Node ID...")
        sel_layout.addWidget(self.dest_combo)

        self.start_btn = QPushButton("Apri Chat")
        self.start_btn.clicked.connect(self.on_start_chat_clicked)
        sel_layout.addWidget(self.start_btn)
        
        content_layout.addWidget(self.selector_widget)

        # 3. Chat log Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        
        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background-color: #0f172a;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        self.chat_layout.setSpacing(10)
        
        # Load More Button
        self.load_more_btn = QPushButton("⬆ Carica messaggi precedenti")
        self.load_more_btn.setStyleSheet("""
            background-color: transparent;
            border: 1px solid #1e293b;
            color: #38bdf8;
            font-size: 11px;
            padding: 6px;
            border-radius: 4px;
        """)
        self.load_more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.load_more_btn.clicked.connect(self.load_more_history)
        self.load_more_btn.setVisible(False)
        self.chat_layout.addWidget(self.load_more_btn)
        
        self.chat_layout.addStretch() # pushing messages down
        
        self.scroll.setWidget(self.chat_container)
        content_layout.addWidget(self.scroll)

        # 4. Message Input Box
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)
        
        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Scrivi un messaggio...")
        self.msg_input.returnPressed.connect(self.send_current_message)
        self.msg_input.setEnabled(False)
        input_layout.addWidget(self.msg_input)
        
        self.send_btn = QPushButton("Invia")
        self.send_btn.clicked.connect(self.send_current_message)
        self.send_btn.setEnabled(False)
        input_layout.addWidget(self.send_btn)
        
        content_layout.addLayout(input_layout)
        main_layout.addWidget(content)

        # Signal hooks
        self.conn.chat_history_received.connect(self.on_chat_history_received)
        self.conn.chat_load_finished.connect(self.on_chat_load_finished)
        self.conn.message_sent_status.connect(self.on_message_sent_status)
        self.conn.nodes_channels_received.connect(self.on_nodes_channels_received)

        # Initial nodes/channels loading
        self.conn.request_nodes_channels()

    def set_chat_target(self, node_id=None, channel_name=None):
        self.clear_chat_bubbles()
        self.offset = 0
        self.target_node = node_id
        self.target_channel = channel_name

        if node_id:
            self.header.title_lbl.setText(f"Chat con {node_id}")
            self.header.sub_lbl.setText("Conversazione privata diretta (DM)")
            self.type_combo.setCurrentIndex(0)
            self.dest_combo.setEditText(node_id)
            self.msg_input.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.load_more_btn.setVisible(True)
            self.load_more_btn.setEnabled(True)
            self.load_more_btn.setText("⬆ Carica messaggi precedenti")
            self.conn.request_chat_history(0, 50, filter_target=node_id)
        elif channel_name:
            self.header.title_lbl.setText(f"Canale {channel_name}")
            self.header.sub_lbl.setText("Messaggi broadcast sul canale mesh")
            self.type_combo.setCurrentIndex(1)
            self.dest_combo.setEditText(channel_name)
            self.msg_input.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.load_more_btn.setVisible(True)
            self.load_more_btn.setEnabled(True)
            self.load_more_btn.setText("⬆ Carica messaggi precedenti")
            self.conn.request_chat_history(0, 50, filter_channel=channel_name)
        else:
            self.header.title_lbl.setText("Nuova Chat")
            self.header.sub_lbl.setText("Seleziona un destinatario o un canale per iniziare")
            self.msg_input.setEnabled(False)
            self.send_btn.setEnabled(False)
            self.load_more_btn.setVisible(False)

    def on_selector_type_changed(self, index):
        self.dest_combo.clear()
        if index == 0: # DM
            self.dest_combo.addItems(self.known_nodes)
        else: # Channel
            self.dest_combo.addItems(self.known_channels)

    def on_start_chat_clicked(self):
        val = self.dest_combo.currentText().strip()
        if not val:
            return
        if self.type_combo.currentIndex() == 0:
            self.set_chat_target(node_id=val)
        else:
            self.set_chat_target(channel_name=val)

    def load_more_history(self):
        self.load_more_btn.setEnabled(False)
        self.load_more_btn.setText("Caricamento...")
        if self.target_node:
            self.conn.request_chat_history(self.offset, 50, filter_target=self.target_node)
        elif self.target_channel:
            self.conn.request_chat_history(self.offset, 50, filter_channel=self.target_channel)

    def clear_chat_bubbles(self):
        for child in self.chat_container.findChildren(ChatBubble):
            self.chat_layout.removeWidget(child)
            child.deleteLater()

    def on_chat_history_received(self, ts, from_node, to_node, channel, text):
        is_outgoing = (from_node == "local_node")
        bubble = ChatBubble(ts, from_node, text, is_outgoing)
        
        # Insert bubbles immediately after the load_more_btn (index 1) to build history backwards
        self.chat_layout.insertWidget(1, bubble)
        self.offset += 1

    def on_chat_load_finished(self, is_last):
        self.load_more_btn.setText("⬆ Carica messaggi precedenti")
        self.load_more_btn.setEnabled(not is_last)
        if is_last:
            self.load_more_btn.setText("Inizio della conversazione raggiunto")
        # Scroll to bottom on initial load
        if self.offset <= 50:
            QTimer.singleShot(100, self.scroll_to_bottom)

    def scroll_to_bottom(self):
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def on_message_sent_status(self, success, error_msg):
        if success:
            self.msg_input.clear()
            self.msg_input.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.msg_input.setFocus()
            QTimer.singleShot(100, self.scroll_to_bottom)
        else:
            self.msg_input.setEnabled(True)
            self.send_btn.setEnabled(True)
            QMessageBox.critical(self, "Errore", f"Impossibile inviare il messaggio: {error_msg}")

    def on_nodes_channels_received(self, nodes, channels, radio_online=False):
        self.known_nodes = nodes
        self.known_channels = channels
        self.header.set_connected(True, is_mock=self.conn.is_mock, radio_online=radio_online)
        self.on_selector_type_changed(self.type_combo.currentIndex())

    def send_current_message(self):
        text = self.msg_input.text().strip()
        if not text:
            return
        
        self.msg_input.setEnabled(False)
        self.send_btn.setEnabled(False)
        
        if self.target_node:
            self.conn.send_message(text, to_node=self.target_node)
        elif self.target_channel:
            self.conn.send_message(text, channel=self.target_channel)

    def append_live_message(self, ts, from_node, to_node, text):
        match = False
        if self.target_node:
            # DM matches if message is from target to us, or from us to target
            if (from_node == self.target_node and to_node != "^all") or (from_node == "local_node" and to_node == self.target_node):
                match = True
        elif self.target_channel:
            # Channel matches if broadcast target matches channel name
            if to_node == "^all" or to_node == self.target_channel:
                match = True
                
        if match:
            is_outgoing = (from_node == "local_node")
            bubble = ChatBubble(ts, from_node, text, is_outgoing)
            # Insert at bottom (just before stretch at count - 1)
            self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
            self.offset += 1
            self.scroll_to_bottom()

    def closeEvent(self, event):
        event.ignore()
        self.hide()


# ─────────────────────────────────────────────────────────────
#  Global Helper: Navigation menu builder
# ─────────────────────────────────────────────────────────────
def create_navigation_menu(window: QMainWindow, on_navigate_cb):
    menubar = window.menuBar()
    nav_menu = menubar.addMenu("🧭  Navigazione")
    
    latest_act = nav_menu.addAction("💬  Ultimi Messaggi")
    latest_act.triggered.connect(lambda: on_navigate_cb("latest"))
    
    archive_act = nav_menu.addAction("📂  Archivio Messaggi")
    archive_act.triggered.connect(lambda: on_navigate_cb("archive"))
    
    chat_act = nav_menu.addAction("✉️  Chat / Invia")
    chat_act.triggered.connect(lambda: on_navigate_cb("chat"))
    
    nav_menu.addSeparator()
    
    exit_act = nav_menu.addAction("❌  Esci")
    exit_act.triggered.connect(lambda: on_navigate_cb("exit"))
