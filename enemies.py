import random
import pygame
import math
from math import inf
from pickups import Pickup

# Pathfinding constants
CELL_SIZE = 20
GRID_WIDTH = 800 // CELL_SIZE
GRID_HEIGHT = 600 // CELL_SIZE

# Blocked cells for organ (approx center 200x200)
blocked_cells = set()
for x in range(15, 26):  # 15*20=300 to 25*20=500
    for y in range(10, 21):  # 10*20=200 to 20*20=400
        blocked_cells.add((x, y))

def pos_to_cell(pos):
    return (int(pos[0] // CELL_SIZE), int(pos[1] // CELL_SIZE))

def cell_to_pos(cell):
    return (cell[0] * CELL_SIZE + CELL_SIZE // 2, cell[1] * CELL_SIZE + CELL_SIZE // 2)

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def get_neighbors(cell):
    x, y = cell
    neighbors = []
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT and (nx, ny) not in blocked_cells:
            # Prevent cutting through diagonal corners of the organ
            if dx != 0 and dy != 0:
                if (x + dx, y) in blocked_cells or (x, y + dy) in blocked_cells:
                    continue
            neighbors.append((nx, ny))
    return neighbors


def find_nearest_free_cell(cell, max_radius=10):
    if cell not in blocked_cells:
        return cell
    for radius in range(1, max_radius + 1):
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                neighbor = (cell[0] + dx, cell[1] + dy)
                if 0 <= neighbor[0] < GRID_WIDTH and 0 <= neighbor[1] < GRID_HEIGHT:
                    if neighbor not in blocked_cells:
                        return neighbor
    return None

def astar(start, goal):
    if start in blocked_cells:
        start = find_nearest_free_cell(start) or start
    if goal in blocked_cells:
        goal = find_nearest_free_cell(goal) or goal
    open_set = [start]
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, goal)}
    while open_set:
        current = min(open_set, key=lambda x: f_score.get(x, inf))
        if current == goal:
            return reconstruct_path(came_from, current)
        open_set.remove(current)
        for neighbor in get_neighbors(current):
            tentative_g = g_score[current] + 1
            if tentative_g < g_score.get(neighbor, inf):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + heuristic(neighbor, goal)
                if neighbor not in open_set:
                    open_set.append(neighbor)
    return []

def reconstruct_path(came_from, current):
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path

def get_dominant_color(surface):
    colors = []
    width, height = surface.get_size()
    for x in range(0, width, max(1, width//10)):
        for y in range(0, height, max(1, height//10)):
            color = surface.get_at((x, y))
            if color.a > 50:
                colors.append((color.r, color.g, color.b))
    if not colors:
        return (255, 255, 255)
    r = sum([c[0] for c in colors]) // len(colors)
    g = sum([c[1] for c in colors]) // len(colors)
    b = sum([c[2] for c in colors]) // len(colors)
    return (r, g, b)

class Virus(pygame.sprite.Sprite):
    def __init__(self, x, y, target_center):
        super().__init__()
        # Load virus sprite
        if not hasattr(Virus, '_base_image'):
            raw_image = pygame.image.load('sprites/virus.png').convert_alpha()
            bbox = raw_image.get_bounding_rect()
            if bbox:
                Virus._base_image = raw_image.subsurface(bbox).copy()
            else:
                Virus._base_image = raw_image
            Virus._base_image = pygame.transform.smoothscale(Virus._base_image, (40, 40))

        self.base_radius = 20
        self.image = Virus._base_image.copy()

        if not hasattr(Virus, '_primary_color'):
            Virus._primary_color = get_dominant_color(self.image)
        self.primary_color = Virus._primary_color

        self.rect = self.image.get_rect(center=(x, y))
        self.mask = pygame.mask.from_surface(self.image)
        self.target = target_center  # Center of the organ
        self.speed = 2
        self.attack_radius = 150
        self.attacking = False
        self.last_attack_time = 0
        self.attack_cooldown = 2000  # 2 seconds in milliseconds
        self.damage_organ = False
        self.health = 1

    def update(self, current_time, player=None, organ=None):
        distance = pygame.math.Vector2(self.rect.center).distance_to(self.target)

        if distance > self.attack_radius:
            self.attacking = False
            direction = pygame.math.Vector2(self.target) - pygame.math.Vector2(self.rect.center)
            if direction.length() > 0:
                direction.normalize_ip()
                self.rect.move_ip(direction * self.speed)
        else:
            self.attacking = True
            if current_time - self.last_attack_time > self.attack_cooldown:
                self.last_attack_time = current_time
                self.damage_organ = True

    def take_damage(self, amount=1, pickups_group=None, all_sprites=None):
        self.health -= amount
        is_dead = self.health <= 0
        if is_dead and pickups_group is not None and all_sprites is not None:
            if random.random() < 0.25:
                pickup_type = random.choice(['speed_boost', 'health'])
                pickup_colors = {
                    'speed_boost': (255, 255, 0),
                    'health': (0, 255, 120),
                }
                pickup = Pickup(self.rect.centerx, self.rect.centery, pickup_type, pickup_colors[pickup_type])
                pickups_group.add(pickup)
                all_sprites.add(pickup)
        return is_dead

    def draw_sweep(self, surface):
        if self.attacking:
            pygame.draw.line(surface, (80, 255, 90), self.rect.center, self.target, 4)


class Stalker(Virus):
    def __init__(self, x, y, target_center):
        super().__init__(x, y, target_center)
        self.speed = 2.5
        self.max_speed = 2.5
        self.damage = 20
        self.health = 1
        self.attack_radius = 0
        if not hasattr(Stalker, '_image_loaded'):
            try:
                raw_image = pygame.image.load('sprites/stalker.png').convert_alpha()
                bbox = raw_image.get_bounding_rect()
                if bbox:
                    stalker_image = raw_image.subsurface(bbox).copy()
                else:
                    stalker_image = raw_image
                Stalker._base_image = pygame.transform.smoothscale(stalker_image, (42, 42))
                self.image = Stalker._base_image.copy()
            except:
                self.image = pygame.Surface((42, 42), pygame.SRCALPHA)
                pygame.draw.circle(self.image, (0, 255, 0), (21, 21), 21)
                Stalker._base_image = self.image.copy()
            Stalker._image_loaded = True
        else:
            self.image = Stalker._base_image.copy()

        if not hasattr(Stalker, '_primary_color'):
            Stalker._primary_color = get_dominant_color(self.image)
        self.primary_color = Stalker._primary_color

        self.rect = self.image.get_rect(center=(x, y))
        self.mask = pygame.mask.from_surface(self.image)
        self.velocity = pygame.math.Vector2(0, 0)
        self.avoid_direction = pygame.math.Vector2(0, 0)
        self.post_hit_recover_until = 0
        self.last_chase_direction = pygame.math.Vector2(1, 0)
        self.path = []
        self.path_index = 0
        self.last_path_time = 0
        self.last_ranged_attack_time = 0
        self.ranged_attack_cooldown = 2400
        self.ranged_attack_range = 340
        self.projectiles = pygame.sprite.Group()

    def update(self, current_time, player=None, organ=None):
        if player is None:
            return

        self.projectiles = pygame.sprite.Group()

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

        if organ is not None:
            if future_rect.colliderect(organ.rect) or organ.rect.clipline(self.rect.center, player.rect.center):
                path_blocked = True

        # Right after a hit, prefer direct pursuit so the stalker does not drift into orbiting.
        if current_time < self.post_hit_recover_until:
            path_blocked = False

        if path_blocked and organ is not None:
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
            # Clear avoidance once the path is free
            self.avoid_direction = self.avoid_direction.lerp(desired, 0.08)
            if self.avoid_direction.length() > 0:
                self.avoid_direction.scale_to_length(1)
            steering = self.avoid_direction

        # Smooth steering
        if steering.length() > 0:
            desired_velocity = steering.normalize() * self.max_speed
            self.velocity = self.velocity.lerp(desired_velocity, 0.12)
            if self.velocity.length() > self.max_speed:
                self.velocity.scale_to_length(self.max_speed)
            self.rect.move_ip(self.velocity)

        # Prevent overlap with the organ
        if organ is not None and self.rect.colliderect(organ.rect):
            push_out = pygame.math.Vector2(self.rect.center) - pygame.math.Vector2(organ.rect.center)
            if push_out.length() == 0:
                push_out = pygame.math.Vector2(1, 0)
            push_out.normalize_ip()
            self.rect.move_ip(push_out * self.max_speed)

        # Check collision with player
        if self.rect.colliderect(player.rect) and current_time - self.last_attack_time > self.attack_cooldown:
            took_hit = False
            if hasattr(player, 'try_take_hit'):
                took_hit = player.try_take_hit(current_time, self.damage)
            elif hasattr(player, 'health'):
                player.health = max(0, player.health - self.damage)
                took_hit = True

            if took_hit:
                self.last_attack_time = current_time
                # Small separation + short direct-chase recovery prevents post-hit orbiting.
                from_player = pygame.math.Vector2(self.rect.center) - pygame.math.Vector2(player.rect.center)
                if from_player.length() == 0:
                    from_player = self.last_chase_direction * -1
                from_player.normalize_ip()
                self.rect.move_ip(from_player * 4)
                self.velocity = self.velocity.lerp(desired * self.max_speed, 0.6)
                self.post_hit_recover_until = current_time + 300

        # Fire boss-style projectile toward the player, but less frequently and less damaging than the boss.
        to_player = pygame.math.Vector2(player.rect.center) - pygame.math.Vector2(self.rect.center)
        if (
            to_player.length() <= self.ranged_attack_range
            and current_time - self.last_ranged_attack_time >= self.ranged_attack_cooldown
        ):
            from boss import BossProjectile

            angle = math.atan2(to_player.y, to_player.x)
            projectile = BossProjectile(self.rect.centerx, self.rect.centery, angle, speed=3.4)
            projectile.damage = 18
            self.projectiles.add(projectile)
            self.last_ranged_attack_time = current_time


class Tank(Virus):
    def __init__(self, x, y, target_center):
        super().__init__(x, y, target_center)
        self.speed = 1.5  # Increased speed
        self.health = 5
        self.attack_radius = 180
        self.base_radius = 28
        # Load tank sprite if available
        if not hasattr(Tank, '_image_loaded'):
            try:
                raw_image = pygame.image.load('sprites/tank.png').convert_alpha()
                bbox = raw_image.get_bounding_rect()
                if bbox:
                    Tank._base_image = raw_image.subsurface(bbox).copy()
                else:
                    Tank._base_image = raw_image
                Tank._base_image = pygame.transform.smoothscale(Tank._base_image, (self.base_radius * 2, self.base_radius * 2))
            except:
                Tank._base_image = pygame.Surface((self.base_radius * 2, self.base_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(Tank._base_image, (200, 200, 200), (self.base_radius, self.base_radius), self.base_radius)
            Tank._image_loaded = True

        self.base_image = Tank._base_image
        self.damage_image = pygame.Surface((self.base_radius * 2, self.base_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.damage_image, (255, 0, 0), (self.base_radius, self.base_radius), self.base_radius)
        self.image = self.base_image.copy()

        if not hasattr(Tank, '_primary_color'):
            Tank._primary_color = get_dominant_color(self.image)
        self.primary_color = Tank._primary_color

        self.rect = self.image.get_rect(center=(x, y))
        self.mask = pygame.mask.from_surface(self.image)
        self.damaged_timer = 0

    def update(self, current_time, player=None, organ=None):
        if self.damaged_timer > 0:
            self.damaged_timer -= 1
            if self.damaged_timer % 4 < 2:
                self.image = self.damage_image.copy()
            else:
                self.image = self.base_image.copy()
        else:
            self.image = self.base_image.copy()
        self.mask = pygame.mask.from_surface(self.image)
        super().update(current_time, player, organ)

    def take_damage(self, amount=1, pickups_group=None, all_sprites=None):
        destroyed = super().take_damage(amount, pickups_group, all_sprites)
        if not destroyed:
            self.damaged_timer = 12
        return destroyed


class ExplosionParticle(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, color=(255, 255, 255)):
        super().__init__()
        self.image = pygame.Surface((6, 6), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (3, 3), 3)
        self.rect = self.image.get_rect(center=(x, y))
        self.velocity = direction * 3  # speed
        self.lifetime = 30  # frames

    def update(self):
        self.rect.move_ip(self.velocity)
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()
        # Fade alpha
        alpha = int(255 * (self.lifetime / 30.0))
        self.image.set_alpha(alpha)