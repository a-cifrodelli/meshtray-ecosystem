# Guida all'Installazione (Meshtray Ecosystem)

Questa guida descrive i requisiti e i passaggi dettagliati per installare, configurare ed avviare sia il **Server** (traduttore MQTT/Seriale e WebSocket) sia il **Client Desktop** (Meshtray GUI).

---

## 📋 Requisiti di Sistema

### Server
* **Sistema Operativo**: Linux (consigliato per produzione, es. Raspberry Pi OS, Debian, Ubuntu, Arch Linux) o Windows (sviluppo).
* **Python**: versione `3.10` o superiore.
* **Broker MQTT**: accesso a un broker MQTT (es. Mosquitto locale, HiveMQ, EMQX) in cui transitano i messaggi di Meshtastic in formato JSON (topic `msh/json/#` o `msh/#`).
* **Hardware Radio (Opzionale)**: un dispositivo Meshtastic (es. Heltec V3, T-Beam, T-Echo, nRF52) collegato via USB/Seriale al server, necessario per la trasmissione radio LoRa in uscita (outbound) e la lettura in tempo reale del NodeDB locale.

### Client (Meshtray)
* **Windows**: Windows 10 o Windows 11 a 64 bit.
* **Linux**: qualsiasi distribuzione desktop moderna con server grafico X11 o Wayland (es. Ubuntu, Debian, Fedora, Arch Linux).
* **Python (solo per avvio da sorgente/sviluppo)**: versione `3.10` o superiore.
* **Nessun requisito Python per la versione binaria compilata** (`Meshtray.exe` o `Meshtray`).

---

## 🛠️ Configurazione del Server

Il server si occupa di:
1. Ricevere ed elaborare i messaggi dal broker MQTT.
2. Salvarli nel database SQLite locale tramite SQLAlchemy/aiosqlite.
3. Inoltrare i messaggi ai nodi radio via seriale LoRa quando richiesto.
4. Esporre i canali WebSocket in tempo reale (notifiche, storico, invio, nodi e canali attivi).

### 1. Preparazione dell'ambiente virtuale
Accedi alla cartella `server/` e crea l'ambiente virtuale dedicato:

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate  # Su Linux/macOS
# Oppure su Windows (PowerShell): .venv\Scripts\Activate.ps1
```

### 2. Installazione delle dipendenze
Installa ed aggiorna le librerie necessarie:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configurazione del file `.env`
Copia il modello predefinito in `server/.env` (o crea un file `.env` nella root del repository):

```bash
cp .env.example .env
# Oppure dalla root:
# cp server/.env.example server/.env
```

#### Dettaglio dei parametri di configurazione del Server:

| Variabile | Default / Esempio | Descrizione |
|---|---|---|
| `MQTT_BROKER` | `broker.hivemq.com` | Indirizzo IP o hostname del broker MQTT. |
| `MQTT_PORT` | `1883` (o `8883` per TLS) | Porta del broker MQTT. |
| `MQTT_USER` | *(vuoto)* | Nome utente per l'autenticazione MQTT (lascia vuoto se anonimo). |
| `MQTT_PASS` | *(vuoto)* | Password per l'autenticazione MQTT. |
| `MQTT_CLIENT_ID` | `meshtray_ecosystem_server` | ID univoco del client per la sessione MQTT. |
| `MQTT_CA_CERTS` | `certs/root_ca.crt` | Percorso del certificato CA se ci si connette con crittografia TLS. |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/messages.db` | Stringa di connessione asincrona SQLite per lo storage locale dei messaggi. |
| `SERIAL_PORT` | `/dev/ttyUSB0` (o `COM3`) | Percorso della porta seriale USB del dispositivo Meshtastic (opzionale). |
| `HOST` | `0.0.0.0` | Indirizzo IP di ascolto per FastAPI/WebSocket (`0.0.0.0` per tutta la LAN). |
| `PORT` | `8088` | Porta di ascolto del servizio WebSocket/HTTP. |

> [!TIP]
> Nel file [`server/config.py`](../server/config.py) è inoltre possibile personalizzare:
> * `IGNORED_CHANNELS`: canali numerici da escludere (default `{"2"}`).
> * La connessione alla porta seriale (`SERIAL_PORT`) rimane aperta in modo permanente finché la radio è collegata, con rilevamento dinamico hot-plug in tempo reale.

### 4. Avvio Manuale del Server

Puoi avviare il server direttamente usando lo script di lancio rapido che prepara automaticamente l'ambiente e passa eventuali argomenti:

```bash
# Su Linux/macOS:
chmod +x launch.sh
./launch.sh

# Con debug hardware radio (stampa i log del firmware Meshtastic a console):
./launch.sh --device-debug
```

Oppure avviando direttamente con l'interprete Python attivo nel venv:
```bash
python main.py
```

---

## ⚙️ Installazione come Servizio Systemd (Linux)

Per far sì che il server si avvii automaticamente in background (ideale su Raspberry Pi o server Linux dedicati), è incluso uno script di installazione interattivo e sicuro:

```bash
chmod +x etc/install_service.sh
./etc/install_service.sh
```

> [!IMPORTANT]
> Esegui lo script **senza `sudo`**. I permessi di amministratore vengono richiesti interattivamente **solo se necessario** (ad esempio quando si sceglie l'installazione a livello di sistema o per un utente diverso).

### Scelta della modalità di installazione:

Lo script propone due modalità con gestione completa dei permessi e cleanup automatico in caso di errore:

| Modalità | Destinazione | Permessi richiesti | Avvio automatico |
|---|---|---|---|
| **1) User Scope** (`systemd --user`) | `~/.config/systemd/user/` | Nessuno (se per l'utente corrente) | All'avvio della sessione utente |
| **2) System Scope** (`systemd --system`) | `/etc/systemd/system/` | Richiede `sudo` (chiesto al momento) | All'avvio della macchina (boot) |

#### Gestione del Servizio Utente (Opzione 1):
```bash
systemctl --user start   meshtray.service
systemctl --user stop    meshtray.service
systemctl --user restart meshtray.service
systemctl --user status  meshtray.service

# Seguire i log in tempo reale:
journalctl --user -u meshtray.service -f
```

> [!TIP]
> Per consentire a un servizio utente di rimanere attivo e avviarsi anche senza una sessione di login interattiva aperta (es. Raspberry Pi headless), abilita il *lingering* per quell'utente:
> ```bash
> sudo loginctl enable-linger $USER
> ```

#### Gestione del Servizio di Sistema (Opzione 2):
```bash
sudo systemctl start   meshtray.service
sudo systemctl stop    meshtray.service
sudo systemctl restart meshtray.service
sudo systemctl status  meshtray.service

# Seguire i log in tempo reale:
journalctl -u meshtray.service -f
```

#### Firewall UFW (Opzionale):
Se sul server Linux è attivo il firewall UFW, puoi applicare il profilo già predisposto in `etc/ufw-meshtray`:
```bash
sudo cp etc/ufw-meshtray /etc/ufw/applications.d/
sudo ufw allow meshtray-websocket
```

---

## 💻 Installazione e Avvio del Client (Meshtray)

Il client desktop PyQt6 può essere eseguito da codice sorgente (consigliato in fase di sviluppo) oppure compilato come singolo file eseguibile autonomo senza dipendenze esterne.

### 1. Configurazione della connessione (`client/.env`)

Di default, Meshtray tenta di connettersi all'indirizzo `ws://localhost:8088`. Se il server risiede su un'altra macchina nella rete locale o da remoto:

1. Crea un file `.env` dentro la cartella `client/` (o nella stessa cartella dell'eseguibile compilato):
   ```env
   WS_BASE_URL=ws://192.168.1.100:8088
   ```
   *(Sostituisci con l'IP effettivo o il dominio del server, es. `wss://meshtasticws.rpi.lan`).*
2. *(Opzionale)* Se usi connessioni sicure `wss://` con un certificato autofirmato, specifica il percorso della CA:
   ```env
   ROOT_CA=certs/root_ca.crt
   ```

---

### Opzione A: Avvio da Codice Sorgente (Sviluppo)

1. Entra nella cartella `client/`.
2. Esegui il launcher automatico, che preparerà il virtual environment e installerà i requisiti:
   * **Su Windows**:
     ```powershell
     .\launch_client.bat
     ```
   * **Su Linux**:
     ```bash
     chmod +x launch_client.sh
     ./launch_client.sh
     ```
3. **Parametri Opzionali**:
   * Modalità Simulatore Mock (senza server reale):
     ```bash
     python main.py --mock --delay 3
     ```

---

### Opzione B: Compilazione in Eseguibile Autonomo (Standalone Build)

Se desideri distribuire o utilizzare Meshtray come singolo file binario portabile (`Meshtray.exe` su Windows o `Meshtray` su Linux) senza richiedere l'installazione di Python:

1. Entra nella cartella `client/`.
2. Avvia lo script di compilazione automatica con PyInstaller:
   * **Su Windows**:
     ```powershell
     .\build_client.bat
     ```
   * **Su Linux**:
     ```bash
     chmod +x build_client.sh
     ./build_client.sh
     ```
3. Lo script genererà il file eseguibile monolitico in `client/Meshtray.exe` (o `client/Meshtray`) e ripulirà automaticamente le cartelle temporanee.
4. **Portabilità al 100%**: Il file binario generato incorpora tutti gli asset e le librerie necessarie (incluso il generatore di avatar in memoria). Puoi spostarlo ed eseguirlo liberamente su qualsiasi macchina target.

---

### Opzione C: Esecuzione del Binario Compilato

1. Posiziona il file `Meshtray.exe` (o `Meshtray` su Linux) in una cartella a tua scelta.
2. *(Opzionale)* Se il server non è su `localhost`, crea un file `.env` accanto all'eseguibile con `WS_BASE_URL=ws://IP_SERVER:8088`.
3. Fai doppio clic sull'eseguibile per avviare Meshtray. L'applicazione mostrerà lo splash screen e si ridurrà automaticamente a icona nel System Tray.
