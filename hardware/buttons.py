"""Input helpers for physical buttons/encoders."""

from __future__ import annotations
import time


class EncoderUnavailable(Exception):
    """Raised when the rotary encoder cannot be initialized."""


class EncoderInput:
    """Poll the ANO rotary encoder + 5-way buttons as a simple D-pad.

    move: -1 (up/ccw), +1 (down/cw), 0 (no move)
    horiz: -1 (left), +1 (right), 0 (no move)
    select: True on Select button press edge
    """

    # Seesaw pin assignments
    PIN_SELECT = 1
    PIN_UP = 2
    PIN_LEFT = 3
    PIN_DOWN = 4
    PIN_RIGHT = 5

    def __init__(
        self,
        addr: int = 0x49,
        debounce_s: float = 0.1,
        move_cooldown_s: float = 0.12,
        step_threshold: int = 1,
        settle_s: float = 0.3,
    ):
        try:
            import board
            from adafruit_seesaw import digitalio, rotaryio, seesaw
        except Exception as exc:
            raise EncoderUnavailable(exc) from exc

        # Initialize I2C and Seesaw
        i2c = board.I2C()
        self.ss = seesaw.Seesaw(i2c, addr=addr)

        # Rotary encoder
        self.encoder = rotaryio.IncrementalEncoder(self.ss)
        self.last_position = self.encoder.position

        # Initialize buttons
        for pin in (self.PIN_SELECT, self.PIN_UP, self.PIN_LEFT, self.PIN_DOWN, self.PIN_RIGHT):
            self._init_button(pin)

        # Map button names to DigitalIO
        self.buttons = {
            "select": digitalio.DigitalIO(self.ss, self.PIN_SELECT),
            "up": digitalio.DigitalIO(self.ss, self.PIN_UP),
            "left": digitalio.DigitalIO(self.ss, self.PIN_LEFT),
            "down": digitalio.DigitalIO(self.ss, self.PIN_DOWN),
            "right": digitalio.DigitalIO(self.ss, self.PIN_RIGHT),
        }
        self.button_states = {name: btn.value for name, btn in self.buttons.items()}

        self.debounce_s = debounce_s
        self.move_cooldown_s = move_cooldown_s
        self.last_event_ts = 0.0
        self.last_move_ts = 0.0
        self.step_threshold = max(1, step_threshold)
        self.start_ts = time.monotonic()
        self.settle_s = settle_s

    def _init_button(self, pin: int) -> None:
        self.ss.pin_mode(pin, self.ss.INPUT_PULLUP)

    def _poll_buttons(self, now: float) -> tuple[int, bool, int]:
        """Check button presses and return (move, select, horiz)."""
        move = 0
        horiz = 0
        select = False

        for name, btn in self.buttons.items():
            val = btn.value  # True = unpressed, False = pressed
            prev = self.button_states[name]

            if val != prev and not val and (now - self.last_event_ts) >= self.debounce_s:
                if name == "select":
                    select = True
                elif name == "up":
                    move = -1
                elif name == "down":
                    move = +1
                elif name == "left":
                    horiz = -1
                elif name == "right":
                    horiz = +1

                self.last_event_ts = now

            self.button_states[name] = val

        return move, select, horiz

    def poll(self) -> tuple[int, bool, int]:
        """Return a tuple of (move, select, horiz) for use in UI."""

        move = 0
        horiz = 0
        select = False

        now = time.monotonic()

        # Allow hardware to settle at startup
        if (now - self.start_ts) < self.settle_s:
            self.last_position = self.encoder.position
            self.button_states = {name: btn.value for name, btn in self.buttons.items()}
            return 0, False, 0

        # Rotation (vertical only)
        pos = self.encoder.position
        diff = pos - self.last_position
        if abs(diff) >= self.step_threshold and (now - self.last_move_ts) >= self.move_cooldown_s:
            self.last_position = pos
            move = -1 if diff < 0 else 1
            self.last_move_ts = now

        # Physical buttons
        btn_move, btn_select, btn_horiz = self._poll_buttons(now)

        if btn_move:
            move = btn_move
        if btn_horiz:
            horiz = btn_horiz
        if btn_select:
            select = True

        return move, select, horiz
