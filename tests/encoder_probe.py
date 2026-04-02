"""Quick manual probe for the ANO encoder + button.

Run (in lightenv):
    python tests/encoder_probe.py --addr 0x49 --btn-pin 6
If the button never fires, try --btn-pin 24.
"""

from __future__ import annotations

import argparse
import time

from hardware.buttons import EncoderInput, EncoderUnavailable


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe ANO encoder over I2C")
    parser.add_argument("--addr", type=lambda x: int(x, 0), default=0x49, help="I2C address (hex or dec)")
    parser.add_argument("--btn-pin", type=int, default=6, help="Button pin on seesaw (e.g., 6 or 24)")
    parser.add_argument("--debounce", type=float, default=0.1, help="Button debounce seconds")
    parser.add_argument("--move-cooldown", type=float, default=0.12, help="Rotation cooldown seconds")
    parser.add_argument("--step-threshold", type=int, default=2, help="Steps required before a move is reported")
    parser.add_argument("--settle", type=float, default=0.3, help="Startup settle time seconds")
    args = parser.parse_args()

    try:
        enc = EncoderInput(
            addr=args.addr,
            button_pin=args.btn_pin,
            debounce_s=args.debounce,
            move_cooldown_s=args.move_cooldown,
            step_threshold=args.step_threshold,
            settle_s=args.settle,
        )
    except EncoderUnavailable as exc:
        print(f"Encoder unavailable: {exc}")
        return

    print(
        f"Watching encoder at 0x{args.addr:02X}, pin {args.btn_pin} (debounce={args.debounce}s, "
        f"cooldown={args.move_cooldown}s, step_threshold={args.step_threshold})"
    )
    try:
        while True:
            move, select = enc.poll()
            if move:
                print(f"move={move} (pos={enc.last_position})")
            if select:
                print("button pressed")
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("Stopped")


if __name__ == "__main__":
    main()
