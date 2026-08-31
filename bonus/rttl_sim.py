"""
rttl_sim.py — Parser e simulatore audio continuo di stringhe RTTTL con output grafico di debug.
"""

import argparse
import re
import sys
import numpy as np
import sounddevice as sd

DEMO_RTTTL = (
    "Keygen90s:d=16,o=5,b=190:"
    "32a4,32c,32e,32a,32c6,32e6,32a6,32e6,32c6,32a,32e,32c,32a4,32c,"
    "32e,32a,32g#4,32b4,32e,32g#,32b,32e6,32g#6,32e6,32b,32g#,32e,32b4,"
    "32g#4,32b4,32e,32g#,32g4,32a#4,32d,32g,32a#,32d6,32g6,32d6,32a#,"
    "32g,32d,32a#4,32g4,32a#4,32d,32g,32f4,32a4,32d,32f,32a,32d6,32f6,"
    "32d6,32a,32f,32d,32a4,16f4,16g4,16g#4,8a4,32a,32c6,32e6,32a6,16e6,"
    "16c6,8b,32g#,32b,32e6,32g#6,16e6,16b,8c6,32a,32c6,32e6,32a6,16g#6,"
    "16f6,16e6,16d6,16c6,16b,2a"
)

# Frequenze standard per l'ottava 4 (A4 = 440 Hz)
NOTE_FREQ_O4: dict[str, float] = {
    'c':  261.63,
    'c#': 277.18,
    'd':  293.66,
    'd#': 311.13,
    'e':  329.63,
    'f':  349.23,
    'f#': 369.99,
    'g':  392.00,
    'g#': 415.30,
    'a':  440.00,
    'a#': 466.16,
    'b':  493.88,
    'p':  0.0,
}

NOTE_RE = re.compile(
    r'^(\d+)?([a-gp])(#?)(\.*)(\d+)?(\.*)$',
    re.IGNORECASE,
)


def _sine(t: np.ndarray, freq: float) -> np.ndarray:
    return np.sin(2 * np.pi * freq * t)


def _square(t: np.ndarray, freq: float) -> np.ndarray:
    return np.sign(np.sin(2 * np.pi * freq * t))


def _triangle(t: np.ndarray, freq: float) -> np.ndarray:
    return 2 * np.abs(2 * (t * freq - np.floor(t * freq + 0.5))) - 1


WAVE_GENERATORS = {
    "sine": _sine,
    "square": _square,
    "triangle": _triangle,
}


def parse_rtttl(rtttl: str) -> tuple[str, int, int, float, list[dict]]:
    rtttl = rtttl.strip()
    parts = rtttl.split(':', 2)
    if len(parts) != 3:
        raise ValueError(
            "Formato RTTTL non valido. Attesi 3 blocchi separati da due punti (:)"
        )

    name_part, header_part, notes_part = parts
    default_d = 4
    default_o = 5
    bpm = 120.0

    for item in header_part.split(','):
        if '=' not in item:
            continue
        key, val = item.strip().lower().split('=', 1)
        if key == 'd':
            default_d = int(val)
        elif key == 'o':
            default_o = int(val)
        elif key == 'b':
            bpm = float(val)

    quarter_sec = 60.0 / bpm
    parsed_notes: list[dict] = []

    for token in notes_part.split(','):
        token = token.strip()
        if not token:
            continue

        m = NOTE_RE.match(token)
        if not m:
            print(f"[WARN] Token ignorato (non valido): '{token}'", file=sys.stderr)
            continue

        length_str, pitch, sharp, dots1, octave_str, dots2 = m.groups()
        length = int(length_str) if length_str else default_d
        dur = (4.0 / length) * quarter_sec

        dots_count = len(dots1) + len(dots2)
        if dots_count > 0:
            dur *= (2.0 - (1.0 / (2 ** dots_count)))

        full_pitch = (pitch + sharp).lower()
        octave = int(octave_str) if octave_str else default_o

        base_freq = NOTE_FREQ_O4.get(full_pitch, 0.0)
        if base_freq > 0:
            freq = base_freq * (2.0 ** (octave - 4))
        else:
            freq = 0.0

        parsed_notes.append({
            "token": token,
            "pitch": full_pitch.upper() if full_pitch != 'p' else "PAUSA",
            "octave": str(octave) if full_pitch != 'p' else "-",
            "freq": freq,
            "duration": dur,
        })

    if not parsed_notes:
        raise ValueError("Nessuna nota valida trovata nella stringa RTTTL.")

    return name_part.strip(), default_d, default_o, bpm, parsed_notes


def print_notes_table(name: str, bpm: float, notes: list[dict], wave: str) -> None:
    total_dur = sum(n["duration"] for n in notes)
    total_notes = len(notes)

    print("\n" + "=" * 76)
    print(f" [RTTTL] Traccia: {name:<12} | BPM: {bpm:<5.0f} | Note: {total_notes:<3} | Durata: {total_dur:.2f}s | Onda: {wave}")
    print("=" * 76)
    print(f" {'#':<4} | {'TOKEN':<8} | {'NOTA':<6} | {'OTT':<3} | {'FREQ (Hz)':<10} | {'DURATA':<7} | {'BARRA GRAFICA'}")
    print("-" * 76)

    for i, item in enumerate(notes, 1):
        idx_str = f"[{i:02d}]"
        token = item["token"]
        pitch = item["pitch"]
        octave = item["octave"]
        freq_str = f"{item['freq']:8.2f}" if item['freq'] > 0 else f"{'---':^8}"
        dur = item["duration"]

        # Barra visuale proporzionale alla durata (1 carattere ogni ~0.04s)
        bar_len = max(1, min(24, int(dur / 0.04)))
        bar_char = "█" if item['freq'] > 0 else "░"
        bar = bar_char * bar_len

        print(f" {idx_str:<4} | {token:<8} | {pitch:<6} | {octave:<3} | {freq_str:<10} | {dur:5.3f}s | {bar}")

    print("-" * 76)
    print(f" Totale eventi processati: {total_notes}\n")


def generate_audio_stream(
    notes: list[dict],
    fs: int = 44100,
    wave: str = "square",
    volume: float = 0.5,
) -> np.ndarray:
    chunks = []
    generator = WAVE_GENERATORS.get(wave, _square)

    for item in notes:
        freq = item["freq"]
        dur = item["duration"]
        n_samples = max(1, int(fs * dur))

        if freq <= 0:
            chunks.append(np.zeros(n_samples, dtype=np.float32))
            continue

        t = np.linspace(0, dur, n_samples, endpoint=False)
        chunk = generator(t, freq).astype(np.float32)

        fade_len = min(int(fs * 0.003), n_samples // 4)
        if fade_len > 0:
            fade_in = np.linspace(0, 1, fade_len, dtype=np.float32)
            fade_out = np.linspace(1, 0, fade_len, dtype=np.float32)
            chunk[:fade_len] *= fade_in
            chunk[-fade_len:] *= fade_out

        chunks.append(chunk * volume)

    # Padding di 200 ms alla fine per garantire il completo scarico del buffer audio
    tail_silence = np.zeros(int(fs * 0.20), dtype=np.float32)
    chunks.append(tail_silence)

    return np.concatenate(chunks)


def play_rtttl(
    rtttl: str,
    wave: str = "square",
    volume: float = 0.5,
    fs: int = 44100,
) -> None:
    name, _, _, bpm, notes = parse_rtttl(rtttl)
    print_notes_table(name, bpm, notes, wave)

    print("[AUDIO] Riproduzione in corso...")
    audio_buffer = generate_audio_stream(notes, fs=fs, wave=wave, volume=volume)
    sd.play(audio_buffer, samplerate=fs)
    sd.wait()
    print("[AUDIO] Riproduzione completata con successo.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Parser e simulatore audio di stringhe RTTTL.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("rtttl", nargs="?", help="Stringa RTTTL")
    group.add_argument("--file", metavar="FILE", help="File di testo con la stringa RTTTL")
    group.add_argument("--demo", action="store_true", help="Riproduce la demo integrata")

    parser.add_argument("--wave", choices=["sine", "square", "triangle"], default="square")
    parser.add_argument("--volume", type=float, default=0.5)
    parser.add_argument("--fs", type=int, default=44100)
    args = parser.parse_args()

    if args.demo:
        rtttl_input = DEMO_RTTTL
    elif args.file:
        with open(args.file, encoding="utf-8") as f:
            rtttl_input = f.read().strip()
    elif args.rtttl:
        rtttl_input = args.rtttl
    else:
        parser.print_help()
        sys.exit(1)

    play_rtttl(rtttl_input, wave=args.wave, volume=max(0.0, min(1.0, args.volume)), fs=args.fs)


if __name__ == "__main__":
    main()