import pygame
import sys

WIDTH, HEIGHT = 800, 480  # landscape

MENU_ITEMS = ["Auto", "Manual", "Settings"]


def main():
    pygame.init()
    pygame.display.set_caption("Camera UI")

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    font = pygame.font.SysFont(None, 40)
    clock = pygame.time.Clock()

    selected = 0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(MENU_ITEMS)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(MENU_ITEMS)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    print(f"Selected: {MENU_ITEMS[selected]}")

        screen.fill((0, 0, 0))

        title = font.render("Camera Home", True, (200, 200, 200))
        title_rect = title.get_rect(center=(WIDTH // 2, 60))
        screen.blit(title, title_rect)

        start_y = 150
        line_h = 50
        for i, label in enumerate(MENU_ITEMS):
            color = (255, 255, 0) if i == selected else (180, 180, 180)
            text = font.render(label, True, color)
            rect = text.get_rect(center=(WIDTH // 2, start_y + i * line_h))
            screen.blit(text, rect)

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
