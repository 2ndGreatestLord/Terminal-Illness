import pygame
import math
from ui_screens import get_font
from resource_utils import resource_path

class Organ(pygame.sprite.Sprite):
    def __init__(self, screen_rect):
        super().__init__()
        # Load organ sprite and scale to 350x350
        self.base_image = pygame.image.load(resource_path('sprites/organ-heart.png')).convert_alpha()
        self.base_image = pygame.transform.scale(self.base_image, (350, 350))
        self.image = self.base_image.copy()

        self.screen_center = screen_rect.center
        self.base_rect = self.base_image.get_rect(center=self.screen_center)
        self.rect = self.image.get_rect(center=self.screen_center)
        self.mask = pygame.mask.from_surface(self.image)

        self.base_max_health = 100
        self.max_health = self.base_max_health
        self.health = self.max_health

        self.current_bpm = 70
        self.target_bpm = 70

    def update_bpm(self, current_state, is_boss_wave):
        """Update target BPM based on game state."""
        # Using 3 as the fallback for PLAYING based on main.py state codes
        if is_boss_wave:
            self.target_bpm = 140
        elif current_state == 3 or current_state == 'PLAYING':
            self.target_bpm = 100
        else:
            self.target_bpm = 70

    def update(self, current_state, is_boss_wave):
        self.update_bpm(current_state, is_boss_wave)

        # Smoothly transition BPM
        self.current_bpm += (self.target_bpm - self.current_bpm) * 0.01

        # Math for the pulse (scale factor)
        pulse = 1.0 + 0.05 * math.sin(2 * math.pi * (self.current_bpm / 60) * (pygame.time.get_ticks() / 1000))

        # Transform size
        new_width = int(self.base_rect.width * pulse)
        new_height = int(self.base_rect.height * pulse)
        new_size = (new_width, new_height)

        self.image = pygame.transform.smoothscale(self.base_image, new_size)

        # Re-center rect and update mask
        self.rect = self.image.get_rect(center=self.screen_center)
        self.mask = pygame.mask.from_surface(self.image)

    def draw_health_bar(self, surface):
        # Render a large, labeled health bar at the top of the screen
        bar_width = 400
        bar_height = 30
        bar_x = (surface.get_width() - bar_width) // 2
        bar_y = 10

        # Background bar (red)
        pygame.draw.rect(surface, (255, 0, 0), (bar_x, bar_y, bar_width, bar_height))

        # Health bar (green)
        health_width = int(bar_width * (self.health / self.max_health))
        pygame.draw.rect(surface, (0, 255, 0), (bar_x, bar_y, health_width, bar_height))

        # Label
        font = pygame.font.SysFont(None, 28, bold=True)
        text = font.render(f"Organ Health: {self.health}/{self.max_health}", True, (0, 0, 0))
        text_rect = text.get_rect(center=(surface.get_width() // 2, bar_y + bar_height // 2))
        surface.blit(text, text_rect)