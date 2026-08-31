## 🎯 Panoramica e Problematiche Risolte

Lo standard testuale per rappresentare le ringtones su Meshtastic è:
### **[Ring Tone Text Transfer Language](https://en.wikipedia.org/wiki/Ring_Tone_Text_Transfer_Language)**

I buzzer piezoelettrici montati su nodi hardware (es. Heltec V3, LilyGO T-Beam, T-Echo) soffrono di una risposta in frequenza limitata:
* **Bassa efficienza acustica sotto i 1000 Hz**: le note basse risultano inudibili o soffocate.
* **Banda ottimale (1.5 kHz – 3.5 kHz)**: corrispondente alle ottave standard RTTTL `5`, `6` e `7`.
* **Hardware monofonico**: i piezo non supportano accordi o note simultanee.

Questo tool converte tracce polifoniche MIDI preservando la melodia principale, quantizzando il ritmo a griglia metrica (fino a 1/32) e correggendo automaticamente l'altezza tonale.

---

## ⚡ Caratteristiche Principali

* **Ispezione Tracce (`--list-tracks`)**: scansiona il file MIDI ed elenca canali, strumenti e numero di eventi per individuare subito la traccia melodica/lead ed escludere parti ritmiche o di basso.
* **Piezo Auto-Fit (`--auto-fit`)**: analizza il pitch medio della sequenza e la traspone all'ottava ottimale per massimizzare il volume e la resa del buzzer.
* **Pitch Shifting Manuale (`--transpose`)**: traspone la melodia di un numero arbitrario di semitoni (es. `+12` per salire di un'ottava).
* **Quantizzazione Deterministica**: allinea le durate a frazioni musicali esatte (note intere, minime, crome, semicrome e note puntate) eliminando micro-pause indesiderate e perdite di note dovute al legato.
* **Simulatore Audio Integrato**: riproduce in tempo reale la stringa generata tramite onda quadra (`square`), sinusoidale (`sine`) o triangolare (`triangle`) con tabella di debug a terminale.

---

## 🚀 Utilizzo

Tutti i comandi sono accessibili tramite il launcher `bonus/run.bat` per Windows o `bonus/run.sh`, richiamare senza argomenti per ottenere la lista.

### 1. Ispezionare le tracce MIDI
#### Visualizza l'elenco degli strumenti presenti nel file:
```bash
run.bat midi canzone.mid --list-tracks
```
### 2. Estrarre e convertire la melodia
#### Converti una traccia specifica con ottimizzazione automatica per il buzzer:
```bash
run.bat midi canzone.mid --track 1 --auto-fit --name MyAlert
```
#### Estrae solo i primi 10 secondi e traspone di un'ottava (+12 semitoni)
```bash
run.bat midi canzone.mid --track 0 --transpose 12 --start 0 --end 10
```
### 3. Testare l'anteprima audio
#### Riproduci la stringa RTTTL convertita con l'onda di simulazione piezo:
```bash
run.bat play "MyAlert:d=4,o=5,b=120:8f#6,8d6,8b,8e6"
```
#### Oppure avvia una suoneria dimostrativa preimpostata (demo):
```bash
run.bat play --demo
```
---

## 📡 Integrazione con Meshtastic
La stringa RTTTL stampata a terminale può essere inviata direttamente al client Meshtastic o configurata tramite CLI / App:
### Esempio di configurazione suoneria via Meshtastic CLI
```bash
meshtastic --set ringtone "converted:d=4,o=5,b=120:8f#6,8d6,8b,8e6"
```
