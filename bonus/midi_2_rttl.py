"""
midi_2_rttl.py — Converte tracce MIDI in RTTTL per buzzer piezoelettrici (Meshtastic / ESP32).
"""

import argparse
import pretty_midi

NOTE_NAMES = ['c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#', 'a', 'a#', 'b']
GRID_DURATIONS = [
    (4.0,   1, False),  # 1/1
    (3.0,   2, True),   # 1/2.
    (2.0,   2, False),  # 1/2
    (1.5,   4, True),   # 1/4.
    (1.0,   4, False),  # 1/4
    (0.75,  8, True),   # 1/8.
    (0.5,   8, False),  # 1/8
    (0.375, 16, True),  # 1/16.
    (0.25,  16, False), # 1/16
    (0.125, 32, False), # 1/32
]


def list_midi_tracks(midi_file: str) -> None:
    midi_data = pretty_midi.PrettyMIDI(midi_file)
    print(f"\n[TRACCE DISPONIBILI] '{midi_file}'")
    print(f" {'ID':<4} | {'STRUMENTO':<25} | {'NOTE':<6} | {'TIPO'}")
    print("-" * 55)
    for idx, inst in enumerate(midi_data.instruments):
        tipo = "Percussioni (Drums)" if inst.is_drum else "Melodico"
        name = inst.name.strip() or pretty_midi.program_to_instrument_name(inst.program)
        print(f" [{idx:02d}] | {name:<25} | {len(inst.notes):<6} | {tipo}")
    print("-" * 55)
    print("Usa --track <ID> per convertire una traccia specifica.\n")


def midi_note_to_rtttl(midi_note: int) -> tuple[str, int]:
    note_idx = midi_note % 12
    octave = (midi_note // 12) - 1
    octave = max(4, min(7, octave))
    return NOTE_NAMES[note_idx], octave


def quarters_to_rtttl(quarters: float) -> tuple[int, bool]:
    if quarters <= 0:
        return 32, False
    best_dur = 4
    best_dot = False
    min_diff = float("inf")
    for q_val, dur, dot in GRID_DURATIONS:
        diff = abs(q_val - quarters)
        if diff < min_diff:
            min_diff = diff
            best_dur = dur
            best_dot = dot
    return best_dur, best_dot


def midi_to_rtttl(
    midi_file: str,
    start_time: float = 0.0,
    end_time: float | None = None,
    bpm: float | None = None,
    default_duration: int = 4,
    default_octave: int = 5,
    name: str = "converted",
    track_index: int | None = None,
    transpose: int = 0,
    auto_fit: bool = False,
) -> str:
    midi_data = pretty_midi.PrettyMIDI(midi_file)

    if bpm is None:
        _, tempo_changes = midi_data.get_tempo_changes()
        if len(tempo_changes) > 0 and tempo_changes[0] > 0:
            bpm = float(tempo_changes[0])
        else:
            bpm = float(midi_data.estimate_tempo()) if midi_data.estimate_tempo() > 0 else 120.0

    raw_notes = []
    instruments = (
        [midi_data.instruments[track_index]]
        if track_index is not None and track_index < len(midi_data.instruments)
        else midi_data.instruments
    )

    for inst in instruments:
        if inst.is_drum:
            continue
        for n in inst.notes:
            if n.end <= start_time:
                continue
            if end_time is not None and n.start >= end_time:
                continue

            start_beat = midi_data.time_to_tick(max(n.start, start_time)) / midi_data.resolution
            end_beat = midi_data.time_to_tick(n.end if end_time is None else min(n.end, end_time)) / midi_data.resolution

            if end_beat > start_beat:
                raw_notes.append((start_beat, end_beat, n.pitch))

    if not raw_notes:
        raise ValueError("Nessuna nota trovata nell'intervallo o nella traccia specificata.")

    # Calcolo auto-trasposizione per frequenza ottimale piezo (target: media su C6 = pitch 72)
    if auto_fit:
        avg_pitch = sum(p for _, _, p in raw_notes) / len(raw_notes)
        shifts = round((72 - avg_pitch) / 12) * 12
        transpose += int(shifts)

    # Applica trasposizione con clamp di sicurezza per il range RTTTL (ottave 4-7 = MIDI 48..95)
    adjusted_notes = []
    for s, e, pitch in raw_notes:
        p_trans = pitch + transpose
        p_trans = max(48, min(95, p_trans))
        adjusted_notes.append((s, e, p_trans))

    adjusted_notes.sort(key=lambda x: (x[0], -x[2]))

    # Monofonizzazione e quantizzazione alla griglia di 1/32
    GRID_STEP = 0.125
    quantize = lambda v: round(v / GRID_STEP) * GRID_STEP

    events: list[tuple[float, float, int]] = []
    for s, e, pitch in adjusted_notes:
        q_start = quantize(s)
        q_end = max(q_start + GRID_STEP, quantize(e))

        if not events:
            events.append((q_start, q_end, pitch))
            continue

        prev_s, prev_e, prev_pitch = events[-1]

        if abs(q_start - prev_s) < (GRID_STEP / 2):
            continue  # Salta la nota più grave in caso di accordo

        if prev_e > q_start:
            events[-1] = (prev_s, q_start, prev_pitch)

        events.append((q_start, q_end, pitch))

    rtttl_tokens: list[str] = []
    cursor = quantize(midi_data.time_to_tick(start_time) / midi_data.resolution)

    for s, e, pitch in events:
        gap = s - cursor
        if gap >= (GRID_STEP - 1e-4):
            dur_p, dot_p = quarters_to_rtttl(gap)
            dur_str = "" if dur_p == default_duration else str(dur_p)
            dot_str = "." if dot_p else ""
            rtttl_tokens.append(f"{dur_str}p{dot_str}")

        note_dur = e - s
        if note_dur > 0:
            note_name, octave = midi_note_to_rtttl(pitch)
            dur, dot = quarters_to_rtttl(note_dur)

            dur_str = "" if dur == default_duration else str(dur)
            oct_str = "" if octave == default_octave else str(octave)
            dot_str = "." if dot else ""

            rtttl_tokens.append(f"{dur_str}{note_name}{oct_str}{dot_str}")

        cursor = e

    clean_name = "".join(c for c in name if c.isalnum() or c in "_-")[:10] or "converted"
    header = f"d={default_duration},o={default_octave},b={int(round(bpm))}"
    return f"{clean_name}:{header}:{','.join(rtttl_tokens)}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Converte MIDI in RTTTL ottimizzato per buzzer piezo.")
    parser.add_argument("midi_file", help="File MIDI di input (.mid)")
    parser.add_argument("--list-tracks", action="store_true", help="Elenca le tracce del MIDI ed esce")
    parser.add_argument("--track", type=int, default=None, metavar="IDX", help="Indice della traccia/canale")
    parser.add_argument("--transpose", type=int, default=0, metavar="SEMITONI", help="Traspone l'intonazione (+12 = +1 ottava)")
    parser.add_argument("--auto-fit", action="store_true", help="Ottimizza automaticamente le ottave per buzzer piezo")
    parser.add_argument("--start", type=float, default=0.0, metavar="SEC")
    parser.add_argument("--end", type=float, default=None, metavar="SEC")
    parser.add_argument("--bpm", type=float, default=None, metavar="BPM")
    parser.add_argument("--octave", type=int, default=5, metavar="OCT")
    parser.add_argument("--duration", type=int, default=4, metavar="DUR")
    parser.add_argument("--name", type=str, default="converted", metavar="NAME")
    args = parser.parse_args()

    if args.list_tracks:
        list_midi_tracks(args.midi_file)
        return

    result = midi_to_rtttl(
        midi_file=args.midi_file,
        start_time=args.start,
        end_time=args.end,
        bpm=args.bpm,
        default_duration=args.duration,
        default_octave=args.octave,
        name=args.name,
        track_index=args.track,
        transpose=args.transpose,
        auto_fit=args.auto_fit,
    )
    print(result)


if __name__ == "__main__":
    main()