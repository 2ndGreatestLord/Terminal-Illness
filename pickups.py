import math
import pygame
from resource_utils import resource_path


class Pickup(pygame.sprite.Sprite):
    _base_images = {}

    def __init__(self, x, y, type_name, color=None):
        super().__init__()
        self.type_name = type_name

        sprite_map = {
            'speed_boost': 'sprites/speed.png',
            'health': 'sprites/health.png',
        }

        if self.type_name in sprite_map and self.type_name not in Pickup._base_images:
            try:
                raw_image = pygame.image.load(resource_path(sprite_map[self.type_name])).convert_alpha()
                bbox = raw_image.get_bounding_rect()
                if bbox:
                    raw_image = raw_image.subsurface(bbox).copy()
                Pickup._base_images[self.type_name] = pygame.transform.smoothscale(raw_image, (24, 24))
            except pygame.error:
                Pickup._base_images[self.type_name] = None

        base_image = Pickup._base_images.get(self.type_name)
        if base_image is not None:
            self.image = base_image.copy()
        else:
            fallback_color = color if color is not None else (255, 255, 255)
            self.image = pygame.Surface((24, 24), pygame.SRCALPHA)
            pygame.draw.rect(self.image, fallback_color, (2, 2, 20, 20))
            pygame.draw.rect(self.image, (255, 255, 255), (2, 2, 20, 20), 2)

        self.rect = self.image.get_rect(center=(x, y))
        self.mask = pygame.mask.from_surface(self.image)
        self.base_y = float(self.rect.centery)
        self.spawn_time = pygame.time.get_ticks()
        self.expire_time_ms = 10000

    def update(self):
        now = pygame.time.get_ticks()
        float_offset = math.sin(now * 0.005) * 5
        self.rect.centery = int(self.base_y + float_offset)

        if now - self.spawn_time >= self.expire_time_ms:
            self.kill()

    def apply_effect(self, player):
        now = pygame.time.get_ticks()

        if self.type_name == 'speed_boost':
            if not hasattr(player, 'base_speed'):
                player.base_speed = player.speed
            stacks = getattr(player, 'speed_boost_stacks', 0) + 1
            player.speed_boost_stacks = stacks
            player.speed = player.base_speed * (1 + 0.5 * stacks)
            player.speed_boost_end_time = now + 7000
        elif self.type_name == 'health':
            # Use player.max_health instead of hardcoded 100 to handle upgrades
            max_hp = getattr(player, 'max_health', 100)
            player.health = min(max_hp, player.health + 20)
