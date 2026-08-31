import sys
import os
import argparse
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QAction, QPixmap
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from config import *
from connection import ConnectionThread
from ui import MainWindow, ArchiveWindow, ChatWindow, create_navigation_menu

class MeshtrayApp:
    def __init__(self, is_mock=False, mock_delay=3.0):
        self.is_mock = is_mock
        self.mock_delay = mock_delay

        # Assicura che l'icona del tray PNG sia pronta
        self._ensure_tray_icon()

        # Inizializzazione della connessione in background
        self.conn = ConnectionThread(is_mock, mock_delay)
        
        # Inizializzazione delle finestre
        self.main_win = MainWindow()
        self.archive_win = ArchiveWindow(self.conn)
        self.chat_win = ChatWindow(self.conn)
        self.last_notification_target = None

        # Configurazione della barra dei menu navigazione centralizzata
        create_navigation_menu(self.main_win, self.handle_navigation)
        create_navigation_menu(self.archive_win, self.handle_navigation)
        create_navigation_menu(self.chat_win, self.handle_navigation)

        # Connessione segnali
        self.conn.message_received.connect(self.on_message_received)
        self.conn.connection_status_changed.connect(self.on_connection_status_changed)
        self.conn.nodes_channels_received.connect(self.main_win.update_sidebar)
        self.conn.nodes_channels_received.connect(self.chat_win.on_nodes_channels_received)

        # Collegamento risposte veloci e click sidebar di MainWindow
        self.main_win.reply_triggered.connect(self.show_chat_for_node)
        self.main_win.channel_reply_triggered.connect(self.show_chat_for_channel)
        self.main_win.node_selected.connect(self.show_chat_for_node)
        self.main_win.channel_selected.connect(self.show_chat_for_channel)

        # Collegamento risposte veloci di ArchiveWindow
        self.archive_win.reply_triggered.connect(self.show_chat_for_node)
        self.archive_win.channel_reply_triggered.connect(self.show_chat_for_channel)

        # Inizializzazione Tray Icon nativa
        self.setup_tray()

        # Avvio connessione websocket
        self.conn.start()

    def _ensure_tray_icon(self):
        """Genera tray-icon.png ad alta risoluzione a partire dall'SVG se presente."""
        src_svg = os.path.normpath(os.path.join(os.path.dirname(TRAY_ICON_PNG), "..", "asset", "tray-icon.svg"))
        if os.path.exists(src_svg):
            try:
                from cairosvg import svg2png
                with open(src_svg, 'rb') as f:
                    svg_data = f.read()
                svg2png(bytestring=svg_data, write_to=TRAY_ICON_PNG, output_width=256, output_height=256)
            except Exception as e:
                print(f"[Tray] Fallita la conversione dell'SVG: {e}")

    def setup_tray(self):
        self.tray = QSystemTrayIcon()
        
        # Usa il tray-icon (mesh neon squircle) per la tray icon come da vincolo
        if os.path.exists(TRAY_ICON_PNG):
            self.tray.setIcon(QIcon(TRAY_ICON_PNG))
        elif os.path.exists(FAVICON_PNG):
            self.tray.setIcon(QIcon(FAVICON_PNG))
        elif os.path.exists(LOGO_APP_PNG):
            self.tray.setIcon(QIcon(LOGO_APP_PNG))

        self.tray.setToolTip("Meshtray Ecosystem")

        # Menu della System Tray
        self.menu = QMenu()
        
        self.status_action = self.menu.addAction("📶  WebSocket: Connesso" if self.is_mock else "📶  WebSocket: Connessione...")
        self.status_action.setEnabled(False)

        self.menu.addSeparator()

        archive_action = self.menu.addAction("📂  Archivio Messaggi")
        archive_action.triggered.connect(self.show_archive_window)

        latest_action = self.menu.addAction("💬  Ultimi Messaggi")
        latest_action.triggered.connect(self.show_main_window)

        chat_menu_action = self.menu.addAction("✉️  Chat / Invia")
        chat_menu_action.triggered.connect(self.show_chat_window)

        self.menu.addSeparator()

        exit_action = self.menu.addAction("❌  Esci")
        exit_action.triggered.connect(self.exit_app)

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.messageClicked.connect(self.on_notification_clicked)
        self.tray.show()

    def on_tray_activated(self, reason):
        # Click sinistro o doppio click apre la finestra Ultimi Messaggi
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_main_window()

    def show_main_window(self):
        self.main_win.show()
        self.main_win.activateWindow()
        self.main_win.raise_()
        self.conn.request_nodes_channels() # Refresh sidebar on show

    def show_archive_window(self):
        self.archive_win.show()
        self.archive_win.activateWindow()
        self.archive_win.raise_()

    def show_chat_window(self):
        self.chat_win.show()
        self.chat_win.activateWindow()
        self.chat_win.raise_()
        self.conn.request_nodes_channels()

    def show_chat_for_node(self, node_id):
        self.show_chat_window()
        self.chat_win.set_chat_target(node_id=node_id)

    def show_chat_for_channel(self, channel_name):
        self.show_chat_window()
        self.chat_win.set_chat_target(channel_name=channel_name)

    def handle_navigation(self, action):
        if action == "latest":
            self.show_main_window()
        elif action == "archive":
            self.show_archive_window()
        elif action == "chat":
            self.show_chat_window()
        elif action == "exit":
            self.exit_app()

    def on_message_received(self, ts, from_node, to_node, channel, text):
        # Se è un messaggio inviato da noi in locale (loopback), lo inoltriamo solo alla chat senza inquinare la vista messaggi ricevuti di MainWindow
        if from_node == "local_node":
            self.chat_win.append_live_message(ts, from_node, to_node, text)
            return

        # Inserisce il messaggio nella finestra principale
        self.main_win.add_message(ts, from_node, to_node, channel, text)

        # Inserisce anche nella chat se aperta con quel destinatario/canale
        self.chat_win.append_live_message(ts, from_node, to_node, text)

        # Richiede un aggiornamento dei nodi attivi
        self.conn.request_nodes_channels()

        # Mostra la notifica desktop nativa se la finestra principale non è attiva/visibile
        if not self.main_win.isActiveWindow() or not self.main_win.isVisible():
            if to_node == "^all" or to_node == "":
                self.last_notification_target = ("channel", channel if channel else "")
            else:
                self.last_notification_target = ("node", from_node)

            # Genera l'identicon geometrico associato al mittente in memoria
            from ui import get_identicon
            img = get_identicon(from_node, 128)
            notif_icon = QIcon(QPixmap.fromImage(img))

            self.tray.showMessage(
                f"Nuovo messaggio da {from_node}",
                text,
                notif_icon,
                TOAST_TIMEOUT
            )

    def on_notification_clicked(self):
        if self.last_notification_target:
            type_, target = self.last_notification_target
            if type_ == "node":
                self.show_chat_for_node(target)
            elif type_ == "channel":
                self.show_chat_for_channel(target)

    def on_connection_status_changed(self, connected):
        self.main_win.set_connected(connected, self.is_mock)
        self.chat_win.header.set_connected(connected, self.is_mock, self.main_win.radio_online)
        if self.is_mock:
            self.status_action.setText("📶  WebSocket: Simulazione (Mock)")
        elif connected:
            self.status_action.setText("📶  WebSocket: Connesso")
            self.conn.request_nodes_channels()
        else:
            self.status_action.setText("📶  WebSocket: Disconnesso")

    def exit_app(self):
        print("[EXIT] Arresto del thread di connessione...")
        self.conn.stop()
        print("[EXIT] Arresto applicazione.")
        QApplication.quit()

if __name__ == "__main__":


    # Forza Windows a usare l'icona dell'applicazione (logo-app) nella barra delle applicazioni (vassoio)
    # Su Windows, forza il sistema ad usare l'icona dell'applicazione nella barra delle applicazioni
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Meshtastic.Meshtray.Ecosystem")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Meshtray Client (PyQt6)")
    parser.add_argument("--mock", action="store_true", help="Genera messaggi simulati in locale")
    parser.add_argument("--delay", type=float, default=3.0, help="Frequenza messaggi mock (secondi)")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Meshtray")
    app.setApplicationDisplayName("Meshtray Ecosystem")
    
    # Controllo istanza singola (Single Instance Check) via QLockFile
    from PyQt6.QtCore import QLockFile, QDir
    lock_path = os.path.join(QDir.tempPath(), "meshtray_client.lock")
    lock_file = QLockFile(lock_path)
    if not lock_file.tryLock(100):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Meshtray")
        msg.setText("Un'istanza di Meshtray è già in esecuzione.")
        if os.path.exists(FAVICON_PNG):
            msg.setWindowIcon(QIcon(FAVICON_PNG))
        msg.exec()
        sys.exit(0)
    
    # Manteniamo il lock in vita legandolo all'istanza di QApplication
    app.lock_file = lock_file
    
    # Imposta l'icona globale a livello di QApplication per la barra delle applicazioni
    if os.path.exists(FAVICON_PNG):
        app.setWindowIcon(QIcon(FAVICON_PNG))

    # Mostra starting_banner.png come splash screen overlay borderless a schermo
    from PyQt6.QtWidgets import QSplashScreen
    from PyQt6.QtCore import QTimer

    splash = None
    if os.path.exists(STARTING_BANNER_PNG):
        pixmap = QPixmap(STARTING_BANNER_PNG)
        splash = QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        splash.show()

    meshtray = MeshtrayApp(is_mock=args.mock, mock_delay=args.delay)
    
    # Chiudi l'overlay a schermo dopo 2.5 secondi
    if splash:
        QTimer.singleShot(2500, splash.close)

    sys.exit(app.exec())
