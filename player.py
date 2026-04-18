import pygame
import math

class Player(pygame.sprite.Sprite):
    def __init__(self, screen_rect):
        super().__init__()
        self.screen_rect = screen_rect
        self.speed = 5.8
        self.move_accel = 1.1
        self.friction = -0.10
        self.pos = pygame.math.Vector2(screen_rect.center)
        self.vel = pygame.math.Vector2(0, 0)
        self.acc = pygame.math.Vector2(0, 0)
        self.facing = pygame.math.Vector2(0, -1)  # Default facing up
        self.aim_angle = -math.pi / 2
        self.aim_vector = pygame.math.Vector2(0, -1)
        self.health = 100
        self.max_health = 100
        self.shield_hits = 0
        self.fire_rate_multiplier = 1.0
        self.level = 1
        self.current_xp = 0
        self.xp_to_next_level = 100
        self.invulnerable_until = 0
        self.blink_until = 0
        self.contact_invuln_ms = 700
        self.hit_blink_ms = 1000
        self.blink_interval_ms = 100
        self.size = 1.0  # Size multiplier for scaling
        self.modifiers = []  # List of applied card modifiers
        self.active_cards = []  # List of selected card types for recalculation

        # Base stats for modifier recalculation
        self.base_speed = self.speed
        self.base_max_health = self.max_health
        self.base_size = self.size

        # Load base player image
        raw_image = pygame.image.load('sprites/player.png').convert_alpha()
        bbox = raw_image.get_bounding_rect()
        if bbox: # Crop empty transparent padding to prevent crunched/invisible 16:9 images
            self.base_image = raw_image.subsurface(bbox).copy()
        else:
            self.base_image = raw_image.copy()

        self.base_image = pygame.transform.smoothscale(self.base_image, (30, 30))

        self._update_image()
        self.rect.center = (round(self.pos.x), round(self.pos.y))

    def gain_xp(self, amount):
        self.current_xp += amount
        leveled_up = False

        while self.current_xp >= self.xp_to_next_level:
            self.current_xp -= self.xp_to_next_level
            self.level += 1
            growth_multiplier = 1.28 + min(0.55, (self.level - 1) * 0.03)
            self.xp_to_next_level = max(1, int(math.ceil(self.xp_to_next_level * growth_multiplier)))
            leveled_up = True

        return leveled_up

    def try_take_hit(self, current_time, damage):
        if current_time < self.invulnerable_until:
            return False

        self.invulnerable_until = current_time + self.contact_invuln_ms
        self.blink_until = current_time + self.hit_blink_ms

        if self.shield_hits > 0:
            self.shield_hits -= 1
        else:
            self.health = max(0, self.health - damage)
        return True

    def is_visible(self, current_time):
        if current_time >= self.blink_until:
            return True
        return ((current_time // self.blink_interval_ms) % 2) == 0

    def _update_image(self):
        # Load player sprite at 30x30 pixels
        self.image = self.base_image.copy()
        if hasattr(self, 'rect') and self.rect:
            old_center = self.rect.center
            self.rect = self.image.get_rect(center=old_center)
        else:
            self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)

    def _update_image_with_size(self, size_multiplier):
        """Update player image with a size multiplier."""
        base_size = 30
        scaled_size = int(base_size * size_multiplier)

        # Scale the base image by the size multiplier
        self.image = pygame.transform.smoothscale(self.base_image, (scaled_size, scaled_size))

        # Update rect, preserving center position
        if hasattr(self, 'rect') and self.rect:
            old_center = self.rect.center
            self.rect = self.image.get_rect(center=old_center)
        else:
            self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)

    def update(self, organ=None, is_respawning=False):
        if is_respawning:
            self.vel.update(0, 0)
            self.acc.update(0, 0)
            self.pos.update(self.rect.center)
            return

        # Keep floating-point position aligned if external code moved rect.center.
        if self.rect.center != (round(self.pos.x), round(self.pos.y)):
            self.pos.update(self.rect.center)
            self.vel.update(0, 0)

        keys = pygame.key.get_pressed()
        mouse_x, mouse_y = pygame.mouse.get_pos()
        dx_mouse = mouse_x - self.pos.x
        dy_mouse = mouse_y - self.pos.y
        self.aim_angle = math.atan2(dy_mouse, dx_mouse)
        self.aim_vector = pygame.math.Vector2(math.cos(self.aim_angle), math.sin(self.aim_angle))

        input_dir = pygame.math.Vector2(0, 0)
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            input_dir.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            input_dir.y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            input_dir.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            input_dir.x += 1

        self.acc.update(0, 0)
        if input_dir.length_squared() > 0:
            self.acc += input_dir.normalize() * self.move_accel

        # Friction makes movement glide to a stop instead of snapping to zero.
        self.acc += self.vel * self.friction

        self.vel += self.acc
        if self.vel.length() > self.speed:
            self.vel.scale_to_length(self.speed)
        elif self.vel.length_squared() < 0.0025:
            self.vel.update(0, 0)

        next_pos = self.pos + self.vel + (0.5 * self.acc)

        old_center = self.rect.center
        self.rect.center = (round(next_pos.x), round(next_pos.y))
        if organ and self.rect.colliderect(organ.rect):
            # Use mask-based collision to only collide with the heart shape, not the transparent areas
            offset_x = self.rect.x - organ.rect.x
            offset_y = self.rect.y - organ.rect.y
            if organ.mask.overlap(self.mask, (offset_x, offset_y)):
                self.rect.center = old_center
                self.pos.update(self.rect.center)
                self.vel.update(0, 0)
                self.acc.update(0, 0)
        else:
            self.pos = next_pos

        # Ensure player cannot move off screen boundaries.
        self.rect.clamp_ip(self.screen_rect)
        self.pos.update(self.rect.center)

        if input_dir.length_squared() > 0:
            self.facing = input_dir.normalize()

        self._update_image()

    def draw_health_bar(self, surface):
        # Small health bar above the player
        bar_width = 40
        bar_height = 5
        bar_x = self.rect.centerx - bar_width // 2
        bar_y = self.rect.top - 10

        # Background bar (red)
        pygame.draw.rect(surface, (255, 0, 0), (bar_x, bar_y, bar_width, bar_height))

        # Health bar (green) - use max_health to handle dynamic max health from upgrades
        max_hp = getattr(self, 'max_health', 100)
        health_width = int(bar_width * (self.health / max(1, max_hp)))
        pygame.draw.rect(surface, (0, 255, 0), (bar_x, bar_y, health_width, bar_height))

