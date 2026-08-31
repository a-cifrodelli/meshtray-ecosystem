#!/bin/bash
# ==================================================
# Meshtray Ecosystem - Installer del Servizio Systemd
# Supporta installazione a livello utente (~/.config/systemd/user/)
# o a livello di sistema (/etc/systemd/system/) con escalation permessi.
# ==================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEMPLATE="$SCRIPT_DIR/meshtray.service.template"
SERVICE_NAME="meshtray.service"

# File generati (per cleanup in caso di errore)
GENERATED=""
INSTALLED=""

# --- Cleanup automatico su errore ---
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo ""
        echo "[CLEANUP] Errore rilevato (exit $exit_code). Rimozione file creati..."
        [ -n "$GENERATED" ] && [ -f "$GENERATED" ] && rm -f "$GENERATED" && echo "  Rimosso: $GENERATED"
        [ -n "$INSTALLED" ] && [ -f "$INSTALLED" ] && {
            if rm -f "$INSTALLED" 2>/dev/null; then
                echo "  Rimosso: $INSTALLED"
            else
                sudo rm -f "$INSTALLED" 2>/dev/null && echo "  Rimosso (sudo): $INSTALLED" || \
                    echo "  [WARN] Impossibile rimuovere $INSTALLED — rimuovilo manualmente."
            fi
        }
        echo "[CLEANUP] Installazione annullata."
    fi
}
trap cleanup EXIT

# --- Banner ---
echo ""
echo "=================================================="
echo "   Meshtray Ecosystem - Installer Systemd Service"
echo "=================================================="
echo ""

# --- Scelta del tipo di installazione ---
echo "Scegli il tipo di installazione (Scope):"
echo ""
echo "  1) User Scope  (systemd --user)"
echo "     → Il servizio viene installato nella cartella home dell'utente."
echo "       Parte all'avvio della sessione utente (o con enable-linger)."
echo ""
echo "  2) System Scope (systemd --system)"
echo "     → Il servizio viene installato a livello globale (/etc/systemd/system/)."
echo "       Parte all'avvio del sistema."
echo ""
read -rp "Scelta [1/2]: " INSTALL_TYPE

case "$INSTALL_TYPE" in
    1)
        SCOPE="user"
        ;;
    2)
        SCOPE="system"
        ;;
    *)
        echo "[ERROR] Scelta non valida. Uscita."
        exit 1
        ;;
esac

echo ""

# --- Raccolta parametri ---

# Utente di sistema che eseguirà il servizio
CURRENT_USER="$(whoami)"
SUDO_ORIGINAL_USER="${SUDO_USER:-$(logname 2>/dev/null || whoami)}"
DEFAULT_USER="$SUDO_ORIGINAL_USER"

read -rp "Utente di sistema che eseguirà il server [${DEFAULT_USER}]: " INPUT_USER
SERVICE_USER="${INPUT_USER:-$DEFAULT_USER}"

# --- Gestione errori: Verifica se l'utente esiste ---
if ! getent passwd "$SERVICE_USER" >/dev/null 2>&1; then
    echo ""
    echo "[ERROR] L'utente '$SERVICE_USER' non esiste nel sistema!"
    echo "        Inserisci un utente valido o crealo prima di procedere."
    exit 1
fi

# Trova la cartella home dell'utente specificato
USER_HOME=$(getent passwd "$SERVICE_USER" | cut -d: -f6)

# Percorso di installazione del progetto
DEFAULT_DIR="${PROJECT_ROOT}"
read -rp "Percorso completo della cartella del progetto [${DEFAULT_DIR}]: " INPUT_DIR
INSTALL_DIR="${INPUT_DIR:-$DEFAULT_DIR}"

# Verifica che la directory esista
if [ ! -d "$INSTALL_DIR" ]; then
    echo ""
    echo "[WARN] La directory '$INSTALL_DIR' non esiste ancora."
    read -rp "Continuare comunque? (s/N): " CONFIRM
    [[ "$CONFIRM" =~ ^[sS]$ ]] || { echo "Installazione annullata."; exit 1; }
fi

# Impostazione cartelle di destinazione in base allo Scope
if [ "$SCOPE" = "user" ]; then
    SYSTEMD_DIR="${USER_HOME}/.config/systemd/user"
else
    SYSTEMD_DIR="/etc/systemd/system"
fi

echo ""
echo "Riepilogo configurazione:"
echo "  Scope:     $([ "$SCOPE" = "user" ] && echo "Utente (--user)" || echo "Sistema (--system)")"
echo "  Utente:    $SERVICE_USER (Home: $USER_HOME)"
echo "  Directory: $INSTALL_DIR"
echo "  Script:    $INSTALL_DIR/server/launch.sh"
echo "  Destinaz.: $SYSTEMD_DIR/$SERVICE_NAME"
echo ""
read -rp "Procedere con l'installazione? (s/N): " FINAL_CONFIRM
[[ "$FINAL_CONFIRM" =~ ^[sS]$ ]] || { echo "Installazione annullata."; exit 1; }

# --- Generazione del file .service temporaneo per installazione ---
echo ""
echo "[1/3] Preparazione file di servizio dal template $TEMPLATE ..."
GENERATED="$SCRIPT_DIR/meshtray.service"

if [ "$SCOPE" = "user" ]; then
    # Per i servizi utente systemd, la direttiva User= non va inserita e il target predefinito è default.target
    sed \
        -e "/User={{USER}}/d" \
        -e "s|{{INSTALL_DIR}}|${INSTALL_DIR}|g" \
        -e "s|WantedBy=multi-user.target|WantedBy=default.target|g" \
        "$TEMPLATE" > "$GENERATED"
else
    sed \
        -e "s|{{USER}}|${SERVICE_USER}|g" \
        -e "s|{{INSTALL_DIR}}|${INSTALL_DIR}|g" \
        "$TEMPLATE" > "$GENERATED"
fi

echo "      File generato:"
cat "$GENERATED"
echo ""

# --- Crea destinazione e installa ---
echo "[2/3] Installazione in $SYSTEMD_DIR ..."
INSTALLED="${SYSTEMD_DIR}/${SERVICE_NAME}"

# Determiniamo se servono i privilegi di root per scrivere
NEED_SUDO=0
if [ "$SCOPE" = "system" ]; then
    # System scope richiede sempre privilegi di root
    if [ "$(id -u)" -ne 0 ]; then
        NEED_SUDO=1
    fi
else
    # User scope richiede privilegi solo se l'utente specificato è diverso da quello corrente
    if [ "$SERVICE_USER" != "$CURRENT_USER" ] && [ "$(id -u)" -ne 0 ]; then
        NEED_SUDO=1
    fi
fi

if [ "$NEED_SUDO" -eq 1 ]; then
    echo ""
    echo "[PERM] La scrittura in '$SYSTEMD_DIR' richiede permessi di amministratore."
    echo "       Verrà richiesta la password per sudo."
    echo ""
    sudo mkdir -p "$SYSTEMD_DIR"
    sudo cp "$GENERATED" "$INSTALLED"
    sudo chmod 644 "$INSTALLED"
    if [ "$SCOPE" = "user" ]; then
        sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$(dirname "$SYSTEMD_DIR")" 2>/dev/null || true
        sudo chown "$SERVICE_USER:$SERVICE_USER" "$INSTALLED"
    fi
else
    mkdir -p "$SYSTEMD_DIR"
    cp "$GENERATED" "$INSTALLED"
    chmod 644 "$INSTALLED"
fi

# Pulizia file temporaneo generato localmente
rm -f "$GENERATED"
GENERATED=""

# --- Attivazione del servizio ---
echo "[3/3] Attivazione del servizio Systemd..."

if [ "$SCOPE" = "user" ]; then
    if [ "$SERVICE_USER" = "$CURRENT_USER" ]; then
        systemctl --user daemon-reload
        systemctl --user enable "$SERVICE_NAME"
    else
        sudo -i -u "$SERVICE_USER" systemctl --user daemon-reload
        sudo -i -u "$SERVICE_USER" systemctl --user enable "$SERVICE_NAME"
    fi
else
    if [ "$NEED_SUDO" -eq 1 ]; then
        sudo systemctl daemon-reload
        sudo systemctl enable "$SERVICE_NAME"
    else
        systemctl daemon-reload
        systemctl enable "$SERVICE_NAME"
    fi
fi

# --- Successo: disabilita cleanup ---
trap - EXIT

echo ""
echo "=================================================================="
echo "  SUCCESSO! Servizio '$SERVICE_NAME' installato ed abilitato."
echo ""
echo "  ⚠️ ATTENZIONE: AZIONE RICHIESTA DALL'UTENTE ⚠️"
echo "  Prima di avviare il servizio, devi configurare il file .env!"
echo "  Copia '$INSTALL_DIR/server/.env.example' in '$INSTALL_DIR/.env'"
echo "  ed inserisci credenziali MQTT e configurazioni di sistema."
echo ""
if [ "$SCOPE" = "user" ]; then
    echo "  Comandi utili per avviare e monitorare il servizio (User Scope):"
    if [ "$SERVICE_USER" = "$CURRENT_USER" ]; then
        echo "    systemctl --user start   $SERVICE_NAME"
        echo "    systemctl --user status  $SERVICE_NAME"
        echo "    journalctl --user -u $SERVICE_NAME -f"
    else
        echo "    sudo -i -u $SERVICE_USER systemctl --user start   $SERVICE_NAME"
        echo "    sudo -i -u $SERVICE_USER systemctl --user status  $SERVICE_NAME"
        echo "    sudo -i -u $SERVICE_USER journalctl --user -u $SERVICE_NAME -f"
    fi
    echo ""
    echo "  Per mantenere attivo il servizio anche dopo il logout utente:"
    echo "    sudo loginctl enable-linger $SERVICE_USER"
else
    echo "  Comandi utili per avviare e monitorare il servizio (System Scope):"
    echo "    sudo systemctl start   $SERVICE_NAME"
    echo "    sudo systemctl status  $SERVICE_NAME"
    echo "    journalctl -u $SERVICE_NAME -f"
fi
echo "=================================================================="
