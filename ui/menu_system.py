# ui/menu_system.py
import sys
import pygame

from ui.screens import HomeScreen

WIDTH, HEIGHT = 800, 480


class UISystem:
    def __init__(self, screen, use_encoder: bool = True):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.current_screen = HomeScreen(self)
        self.encoder = None

        if use_encoder:
            try:
                # Lazy import so desktop dev without hardware still works
                from hardware.buttons import EncoderInput

                self.encoder = EncoderInput()
                print("[UI] Hardware encoder active")
            except Exception as exc:
                err_cls = getattr(exc, "__class__", type(exc)).__name__
                print(f"[UI] Encoder unavailable ({err_cls}): {exc}. Using keyboard.")
                self.encoder = None

    def run(self):
        running = True
        while running:
            self._poll_encoder()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                else:
                    self.current_screen.handle_event(event)

            self.current_screen.update()
            self.current_screen.draw(self.screen)

            pygame.display.flip()
            # 60 FPS helps smooth input without adding much CPU
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

    def _poll_encoder(self):
        if not self.encoder:
            return

        move, select = self.encoder.poll()

        if move:
            key = pygame.K_DOWN if move > 0 else pygame.K_UP
            evt = pygame.event.Event(pygame.KEYDOWN, key=key)
            self.current_screen.handle_event(evt)

        if select:
            evt = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
            self.current_screen.handle_event(evt)


def main():
    pygame.init()
    pygame.display.set_caption("Camera UI")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    ui = UISystem(screen)
    ui.run()


if __name__ == "__main__":
    main()
