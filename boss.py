import pygame
import math
import random
from pickups import Pickup
from enemies import get_dominant_color
from resource_utils import resource_path

class BossProjectile(pygame.sprite.Sprite):
    """Projectile fired by the boss during radial blast."""

    def __init__(self, x, y, angle, speed=5):
        super().__init__()
        self.speed = speed
        self.angle = angle
        self.damage = 25  # Boss projectiles deal significant damage

        # Load boss projectile image
        if not hasattr(BossProjectile, '_base_image'):
            raw_image = pygame.image.load(resource_path('sprites/bossprojectile.png')).convert_alpha()
            bbox = raw_image.get_bounding_rect()
            if bbox:
                BossProjectile._base_image = raw_image.subsurface(bbox).copy()
            else:
                BossProjectile._base_image = raw_image

        size = 12
        self.image = pygame.transform.smoothscale(BossProjectile._base_image, (size, size))

        self.rect = self.image.get_rect(center=(x, y))
        self.mask = pygame.mask.from_surface(self.image)
        self.velocity = pygame.math.Vector2(
            math.cos(angle) * speed,
            math.sin(angle) * speed
        )
        self.lifetime = 5000  # 5 seconds in milliseconds
        self.spawn_time = pygame.time.get_ticks()

    def update(self):
        """Update projectile position and check lifetime."""
        self.rect.x += self.velocity.x
        self.rect.y += self.velocity.y

        # Remove if lifetime expired
        if pygame.time.get_ticks() - self.spawn_time > self.lifetime:
            self.kill()


class Boss(pygame.sprite.Sprite):
    """Boss enemy with attacks and obstacle avoidance."""

    def __init__(self, x, y, screen_rect, organ=None):
        super().__init__()
        self.screen_rect = screen_rect
        self.organ = organ

        # Visual properties
        self.radius = 120

        # Load the boss sprite
        if not hasattr(Boss, '_base_image'):
            raw_image = pygame.image.load(resource_path('sprites/boss.png')).convert_alpha()
            Boss._base_image = pygame.transform.smoothscale(raw_image, (240, 240))

        self.base_image = Boss._base_image.copy()
        self.image = self.base_image.copy()

        if not hasattr(Boss, '_primary_color'):
            Boss._primary_color = get_dominant_color(self.image)
        self.primary_color = Boss._primary_color

        self.rect = self.image.get_rect(center=(x, y))
        self.mask = pygame.mask.from_surface(self.image)

        # Health system
        self.health = 500
        self.max_health = 500

        # State management
        self.is_active = True  # Boss is immediately active (no awakening stage)

        # Movement
        self.velocity = pygame.math.Vector2(0, 0)
        self.max_speed = 2.0
        self.avoid_direction = pygame.math.Vector2(1, 0)
        self.last_chase_direction = pygame.math.Vector2(1, 0)

        # Attacks
        self.last_blast_time = 0
        self.blast_cooldown = 3000  # 3 seconds
        self.last_spawn_time = 0
        self.spawn_cooldown = 6000  # 6 seconds
        self.initial_spawn_done = False  # Track if we've spawned the initial minions

        # Track reflected projectiles to prevent double-reflection
        self.recently_reflected = set()

        # Storage for spawned entities this frame
        self.projectiles = pygame.sprite.Group()
        self.spawned_enemies = []

    def update(self, current_time, player=None, organ=None):
        """Update boss state, movement, and attacks."""
        current_time_ticks = pygame.time.get_ticks()

        # Initial spawn: Spawn 2 stalkers + 4 viruses on first update (off-map)
        spawned_enemies = []
        if not self.initial_spawn_done:
            from enemies import Virus, Stalker

            # Use larger offset to ensure minions spawn well off-map
            # This accounts for boss radius + ensures visibility only when entering screen
            offset_distance = 200

            # Spawn 2 stalkers
            for _ in range(2):
                offset_angle = random.uniform(0, 2 * math.pi)
                spawn_x = self.rect.centerx + math.cos(offset_angle) * offset_distance
                spawn_y = self.rect.centery + math.sin(offset_angle) * offset_distance
                target = self.organ.rect.center if self.organ else (self.rect.centerx, self.rect.centery)
                enemy = Stalker(spawn_x, spawn_y, target)
                spawned_enemies.append(enemy)

            # Spawn 4 viruses
            for _ in range(4):
                offset_angle = random.uniform(0, 2 * math.pi)
                spawn_x = self.rect.centerx + math.cos(offset_angle) * offset_distance
                spawn_y = self.rect.centery + math.sin(offset_angle) * offset_distance
                target = self.organ.rect.center if self.organ else (self.rect.centerx, self.rect.centery)
                virus = Virus(spawn_x, spawn_y, target)
                spawned_enemies.append(virus)

            self.initial_spawn_done = True
            self.last_spawn_time = current_time_ticks  # Reset spawn timer after initial spawn

        self.image = self.base_image.copy()

        # Update collision mask after potential image changes
        self.mask = pygame.mask.from_surface(self.image)

        # Movement with obstacle avoidance
        if player is not None:
            self._update_movement(player, organ, current_time_ticks)

        # Attacks
        projectiles = pygame.sprite.Group()
        if current_time_ticks - self.last_blast_time > self.blast_cooldown:
            projectiles = self._fire_radial_blast()
            self.last_blast_time = current_time_ticks

        # Mitosis spawn (normal 6-second cycle after initial spawn)
        if current_time_ticks - self.last_spawn_time > self.spawn_cooldown:
            spawned_enemies.extend(self._spawn_minion())
            self.last_spawn_time = current_time_ticks

        self.projectiles = projectiles
        self.spawned_enemies = spawned_enemies

    def _update_movement(self, player, organ, current_time):
        """Update boss position using obstacle avoidance logic."""
        position = pygame.math.Vector2(self.rect.center)
        desired = pygame.math.Vector2(player.rect.center) - position

        if desired.length() > 0:
            desired.normalize_ip()
            self.last_chase_direction = desired
        else:
            desired = self.last_chase_direction

        steering = desired
        path_blocked = False
        future_rect = self.rect.copy()
        predict = desired * self.max_speed

        if self.velocity.length() > 0:
            predict += self.velocity * 0.6

        future_rect.center = (position + predict)

        # Check if path to player would collide with organ
        if organ is not None:
            if future_rect.colliderect(organ.rect) or organ.rect.clipline(self.rect.center, player.rect.center):
                path_blocked = True

        if path_blocked and organ is not None:
            # Calculate tangent direction to orbit around organ
            offset = position - pygame.math.Vector2(organ.rect.center)
            if offset.length() == 0:
                offset = pygame.math.Vector2(1, 0)
            offset.normalize_ip()
            tangent = pygame.math.Vector2(-offset.y, offset.x)

            if tangent.dot(desired) < 0:
                tangent = -tangent

            self.avoid_direction = self.avoid_direction.lerp(tangent, 0.18)
            if self.avoid_direction.length() == 0:
                self.avoid_direction = tangent
            self.avoid_direction.normalize_ip()
            steering = self.avoid_direction
        else:
            # Clear avoidance once path is free
            self.avoid_direction = self.avoid_direction.lerp(desired, 0.08)
            if self.avoid_direction.length() > 0:
                self.avoid_direction.scale_to_length(1)
            steering = self.avoid_direction

        # Apply velocity
        self.velocity = steering * self.max_speed
        self.rect.move_ip(self.velocity)

        # Keep boss in screen bounds
        self.rect.clamp_ip(self.screen_rect)

    def _fire_radial_blast(self):
        """Fire 12 projectiles in a 360-degree spread."""
        projectiles = pygame.sprite.Group()
        num_projectiles = 12
        angle_step = (2 * math.pi) / num_projectiles

        for i in range(num_projectiles):
            angle = i * angle_step
            projectile = BossProjectile(
                self.rect.centerx,
                self.rect.centery,
                angle,
                speed=4
            )
            projectiles.add(projectile)

        return projectiles

    def _spawn_minion(self):
        """Spawn 2 stalkers + 4 viruses at the boss's location (Mitosis)."""
        # Import here to avoid circular imports
        from enemies import Virus, Stalker

        spawned = []
        offset_distance = 100

        # Spawn 2 stalkers
        for _ in range(2):
            offset_angle = random.uniform(0, 2 * math.pi)
            spawn_x = self.rect.centerx + math.cos(offset_angle) * offset_distance
            spawn_y = self.rect.centery + math.sin(offset_angle) * offset_distance
            target = self.organ.rect.center if self.organ else (self.rect.centerx, self.rect.centery)
            enemy = Stalker(spawn_x, spawn_y, target)
            spawned.append(enemy)

        # Spawn 4 viruses
        for _ in range(4):
            offset_angle = random.uniform(0, 2 * math.pi)
            spawn_x = self.rect.centerx + math.cos(offset_angle) * offset_distance
            spawn_y = self.rect.centery + math.sin(offset_angle) * offset_distance
            target = self.organ.rect.center if self.organ else (self.rect.centerx, self.rect.centery)
            virus = Virus(spawn_x, spawn_y, target)
            spawned.append(virus)

        return spawned

    def take_damage(self, amount):
        """Apply damage to boss (returns True if boss dies)."""
        self.health -= amount
        return self.health <= 0

    def draw_health_bar(self, surface):
        """Draw health bar above the boss."""
        bar_width = 150
        bar_height = 15
        bar_x = self.rect.centerx - bar_width // 2
        bar_y = self.rect.top - 30

        # Background bar (red)
        pygame.draw.rect(surface, (255, 0, 0), (bar_x, bar_y, bar_width, bar_height))

        # Health bar (green)
        health_width = int(bar_width * (max(0, self.health) / self.max_health))
        pygame.draw.rect(surface, (0, 255, 0), (bar_x, bar_y, health_width, bar_height))

        # Border
        pygame.draw.rect(surface, (255, 255, 255), (bar_x, bar_y, bar_width, bar_height), 2)

    def draw(self, surface):
        """Draw boss with health bar."""
        # Draw main boss circle
        surface.blit(self.image, self.rect)
        self.mask = pygame.mask.from_surface(self.image)

        # Draw health bar
        self.draw_health_bar(surface)


# Example usage in main.py would be:
# from boss import Boss
# boss = Boss(400, 150, screen_rect, organ)
# In main loop:
# boss.update(current_time, player, organ)
# if hasattr(boss, 'projectiles'):
#     boss_projectiles_group.add(boss.projectiles)
# boss.draw(screen)
