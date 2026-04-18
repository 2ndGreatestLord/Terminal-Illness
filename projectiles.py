import pygame
import math
from soundmanager import SoundManager
from resource_utils import resource_path


def _load_cropped_image(path):
    image = pygame.image.load(resource_path(path)).convert_alpha()
    bbox = image.get_bounding_rect()
    if bbox:
        return image.subsurface(bbox).copy()
    return image


def _scale_to_max_dim(surface, max_dim):
    width, height = surface.get_size()
    largest = max(width, height)
    if largest <= 0:
        return surface.copy()
    scale = float(max_dim) / float(largest)
    target = (max(1, int(width * scale)), max(1, int(height * scale)))
    return pygame.transform.smoothscale(surface, target)

class Antibody(pygame.sprite.Sprite):
    base_cooldown_ms = 250
    recoil_strength = 0.45
    _last_shot_ms = 0
    acquisition_radius = 200
    close_quarter_radius = 30
    steering_strength = 0.1
    max_steer_angle_degrees = 45

    def __init__(self, x, y, angle, screen_rect, target=None, player=None):
        super().__init__()
        # Base antibody properties
        self.angle = angle
        self.speed = 10
        self.size = 10  # Default size (diameter of circle)
        self.damage = 1  # Default damage
        self.pierce_count = 0  # Default pierce count (0 = no piercing)

        # Apply player modifiers to this antibody
        if player:
            if hasattr(player, 'antibody_size_multiplier'):
                self.size = int(10 * player.antibody_size_multiplier)
            if hasattr(player, 'antibody_damage_multiplier'):
                self.damage = player.antibody_damage_multiplier
            if hasattr(player, 'antibody_speed_multiplier'):
                self.speed = max(1.0, self.speed * player.antibody_speed_multiplier)
            if hasattr(player, 'antibody_pierce_count'):
                self.pierce_count = player.antibody_pierce_count

        # Load and scale antibody image
        if not hasattr(Antibody, '_base_image'):
            raw_image = pygame.image.load(resource_path('sprites/playerprojectile.png')).convert_alpha()
            bbox = raw_image.get_bounding_rect()
            if bbox:
                Antibody._base_image = raw_image.subsurface(bbox).copy()
            else:
                Antibody._base_image = raw_image

        self.image = pygame.transform.smoothscale(Antibody._base_image, (self.size, self.size))
        self.rect = self.image.get_rect(center=(x, y))
        self.mask = pygame.mask.from_surface(self.image)

        self.trail_positions = []

        self.velocity = pygame.math.Vector2(
            math.cos(self.angle) * self.speed,
            math.sin(self.angle) * self.speed,
        )
        self.target = target
        self.homing_active = target is not None
        self.screen_rect = screen_rect

    @classmethod
    def _compute_cooldown_ms(cls, player):
        fire_rate_multiplier = max(0.1, float(getattr(player, 'fire_rate_multiplier', 1.0)))
        cooldown_ms = int(cls.base_cooldown_ms / fire_rate_multiplier)

        cooldown_multiplier = float(getattr(player, 'cooldown_multiplier', 1.0))
        cooldown_ms = int(cooldown_ms * cooldown_multiplier)
        return cooldown_ms

    @classmethod
    def _find_mouse_target(cls, enemies_group):
        mouse_pos = pygame.math.Vector2(pygame.mouse.get_pos())
        target = None

        if enemies_group:
            nearest_mouse_dist_sq = float('inf')
            for enemy in enemies_group:
                if not hasattr(enemy, 'rect'):
                    continue
                dist_sq = (pygame.math.Vector2(enemy.rect.center) - mouse_pos).length_squared()
                if dist_sq < nearest_mouse_dist_sq:
                    nearest_mouse_dist_sq = dist_sq
                    target = enemy

        return target

    @classmethod
    def _play_shoot_sound(cls):
        try:
            sound_manager = SoundManager.get_instance()
            if sound_manager and 'shoot' in sound_manager.sounds:
                sound_manager.play('shoot')
        except Exception as e:
            print(f"Error playing shoot sound: {e}")

    @classmethod
    def _apply_recoil(cls, player, shot_angle):
        shot_dir = pygame.math.Vector2(math.cos(shot_angle), math.sin(shot_angle))
        moving = hasattr(player, 'vel') and player.vel.length_squared() > 0.01
        if moving:
            recoil_vec = -shot_dir * cls.recoil_strength
            player.vel += recoil_vec
            if hasattr(player, 'pos'):
                player.pos += recoil_vec
                player.rect.center = (round(player.pos.x), round(player.pos.y))

    @classmethod
    def _begin_shot(cls, player, enemies_group):
        now = pygame.time.get_ticks()
        cooldown_ms = cls._compute_cooldown_ms(player)

        if now - cls._last_shot_ms < cooldown_ms:
            return None

        shot_angle = float(getattr(player, 'aim_angle', -math.pi / 2))
        target = cls._find_mouse_target(enemies_group)
        cls._last_shot_ms = now
        return shot_angle, target

    @classmethod
    def fire_from_player(cls, player, screen_rect, enemies_group=None):
        fire_context = cls._begin_shot(player, enemies_group)
        if fire_context is None:
            return None

        shot_angle, target = fire_context
        antibody = cls(player.rect.centerx, player.rect.centery, shot_angle, screen_rect, target, player)

        cls._play_shoot_sound()
        cls._apply_recoil(player, shot_angle)

        return antibody

    @classmethod
    def fire_scattershot_from_player(cls, player, screen_rect, enemies_group=None):
        fire_context = cls._begin_shot(player, enemies_group)
        if fire_context is None:
            return []

        shot_angle, target = fire_context
        spread = math.radians(12)
        shot_angles = [shot_angle, shot_angle - spread, shot_angle + spread]

        volley = [
            cls(player.rect.centerx, player.rect.centery, angle, screen_rect, target, player)
            for angle in shot_angles
        ]

        cls._play_shoot_sound()
        cls._apply_recoil(player, shot_angle)
        return volley

    def update(self, enemies_group=None):
        if self.homing_active and self.target is not None:
            # If target is gone, keep current trajectory with no further steering.
            if not getattr(self.target, 'alive', lambda: False)():
                self.homing_active = False
            else:
                bullet_pos = pygame.math.Vector2(self.rect.center)
                to_target = pygame.math.Vector2(self.target.rect.center) - bullet_pos
                dist_to_target = to_target.length()

                # Close-quarter lock: stop steering near center to avoid loops.
                if dist_to_target <= self.close_quarter_radius:
                    self.homing_active = False
                elif dist_to_target <= self.acquisition_radius and dist_to_target > 0:
                    desired_velocity = to_target.normalize() * self.speed
                    velocity_dir = self.velocity.normalize() if self.velocity.length_squared() > 0 else desired_velocity.normalize()
                    target_dir = to_target.normalize()
                    dot = max(-1.0, min(1.0, velocity_dir.dot(target_dir)))
                    angle_degrees = math.degrees(math.acos(dot))

                    if angle_degrees < self.max_steer_angle_degrees:
                        steer = (desired_velocity - self.velocity) * self.steering_strength
                        self.velocity += steer
                        if self.velocity.length_squared() > 0:
                            self.velocity.scale_to_length(self.speed)

        # Move in the velocity direction.
        self.rect.move_ip(self.velocity)

        # Track position for the trail effect (max 5)
        self.trail_positions.append(self.rect.center)
        if len(self.trail_positions) > 5:
            self.trail_positions.pop(0)

        # Kill if it leaves the screen
        if (self.rect.right < 0 or self.rect.left > self.screen_rect.width or
            self.rect.bottom < 0 or self.rect.top > self.screen_rect.height):
            self.kill()

    def draw(self, surface):
        num_positions = len(self.trail_positions)
        if num_positions == 0:
            surface.blit(self.image, self.rect)
            return

        for i, pos in enumerate(self.trail_positions):
            # Calculate position in the 1-to-5 scale
            virtual_idx = i + (5 - num_positions)

            # Opacity from 20% to 100%
            alpha_percent = (virtual_idx + 1) / 5.0
            alpha = int(255 * alpha_percent)

            trail_img = self.image.copy()
            trail_img.set_alpha(alpha)

            # Interpolate tint: Oldest is Magenta (255, 0, 255), Newest is White (255, 255, 255)
            # G channel goes from 0 at virtual_idx 0 to 255 at virtual_idx 4
            g_val = int(255 * (virtual_idx / 4.0)) if virtual_idx < 4 else 255

            tint = pygame.Surface(trail_img.get_size(), pygame.SRCALPHA)
            tint.fill((255, g_val, 255, 255))
            trail_img.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

            rect = trail_img.get_rect(center=pos)
            surface.blit(trail_img, rect)


class EnemyMuzzleFlash(pygame.sprite.Sprite):
    _base_image = None

    def __init__(self, start_pos, target_pos, scale=1.0, lifetime_ms=200):
        super().__init__()
        if EnemyMuzzleFlash._base_image is None:
            EnemyMuzzleFlash._base_image = _load_cropped_image('sprites/muzzle.png')

        self.center = pygame.math.Vector2(start_pos)
        self.target = pygame.math.Vector2(target_pos)
        self.base_scale = scale
        self.lifetime_ms = lifetime_ms
        self.spawn_time = pygame.time.get_ticks()

        direction = self.target - self.center
        if direction.length_squared() <= 0:
            direction = pygame.math.Vector2(1, 0)
        self.angle = math.degrees(math.atan2(-direction.y, direction.x))

        self.image = EnemyMuzzleFlash._base_image.copy()
        self.rect = self.image.get_rect(center=(round(self.center.x), round(self.center.y)))
        self._refresh_image(1.0)

    def _refresh_image(self, factor):
        factor = max(0.05, factor)
        src = EnemyMuzzleFlash._base_image
        base_max_dim = 30 + int(22 * self.base_scale)
        scaled = _scale_to_max_dim(src, max(6, int(base_max_dim * factor)))
        self.image = pygame.transform.rotate(scaled, self.angle)
        self.rect = self.image.get_rect(center=(round(self.center.x), round(self.center.y)))

    def update(self):
        elapsed = pygame.time.get_ticks() - self.spawn_time
        if elapsed >= self.lifetime_ms:
            self.kill()
            return
        progress = elapsed / float(self.lifetime_ms)
        self._refresh_image(1.0 - progress)


class CorrosiveStain(pygame.sprite.Sprite):
    _base_image = None

    def __init__(self, position, attacker=None, scale=1.0):
        super().__init__()
        if CorrosiveStain._base_image is None:
            sheet = _load_cropped_image('sprites/splatter.png')
            frame_w = max(1, sheet.get_width() // 8)
            frame_h = sheet.get_height()
            frame = sheet.subsurface((0, 0, frame_w, frame_h)).copy()
            frame_bbox = frame.get_bounding_rect()
            if frame_bbox:
                frame = frame.subsurface(frame_bbox).copy()
            tint = pygame.Surface(frame.get_size(), pygame.SRCALPHA)
            tint.fill((65, 110, 65, 215))
            frame.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            CorrosiveStain._base_image = frame

        self.attacker = attacker
        self.image = _scale_to_max_dim(CorrosiveStain._base_image, max(12, int(34 * scale)))
        self.rect = self.image.get_rect(center=(round(position[0]), round(position[1])))

    def update(self):
        if self.attacker is not None and not self.attacker.alive():
            self.kill()


class SplatterImpact(pygame.sprite.Sprite):
    _sheet_frames = None

    def __init__(self, position, persist_group, attacker=None, scale=1.0, frame_ms=40):
        super().__init__()
        if SplatterImpact._sheet_frames is None:
            sheet = _load_cropped_image('sprites/splatter.png')
            frame_w = max(1, sheet.get_width() // 8)
            frame_h = sheet.get_height()
            SplatterImpact._sheet_frames = []
            for idx in range(8):
                frame = sheet.subsurface((idx * frame_w, 0, frame_w, frame_h)).copy()
                frame_bbox = frame.get_bounding_rect()
                if frame_bbox:
                    frame = frame.subsurface(frame_bbox).copy()
                SplatterImpact._sheet_frames.append(frame)

        self.persist_group = persist_group
        self.attacker = attacker
        self.position = (round(position[0]), round(position[1]))
        self.scale = scale
        self.frame_ms = frame_ms
        self.spawn_time = pygame.time.get_ticks()
        self.frame_index = 0

        self.frames = []
        for frame in SplatterImpact._sheet_frames:
            scaled = _scale_to_max_dim(frame, max(12, int(40 * self.scale)))
            self.frames.append(scaled)

        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=self.position)

    def update(self):
        elapsed = pygame.time.get_ticks() - self.spawn_time
        next_index = min(len(self.frames) - 1, elapsed // self.frame_ms)
        if next_index != self.frame_index:
            self.frame_index = next_index
            self.image = self.frames[self.frame_index]
            self.rect = self.image.get_rect(center=self.position)

        if elapsed >= self.frame_ms * len(self.frames):
            self.persist_group.add(CorrosiveStain(self.position, attacker=self.attacker, scale=self.scale))
            self.kill()


class EnemyThornProjectile(pygame.sprite.Sprite):
    _base_image = None

    def __init__(
        self,
        start_pos,
        target_pos,
        attacker=None,
        speed=7.0,
        damage=10,
        sine_amplitude=0.0,
        sine_frequency=0.28,
        sprite_scale=1.0,
        trail_len=8,
        is_tank=False,
    ):
        super().__init__()
        if EnemyThornProjectile._base_image is None:
            EnemyThornProjectile._base_image = _load_cropped_image('sprites/thorn.png')

        self.attacker = attacker
        self.damage = damage
        self.speed = float(speed)
        self.sine_amplitude = float(sine_amplitude)
        self.sine_frequency = float(sine_frequency)
        self.is_tank = is_tank

        self.start = pygame.math.Vector2(start_pos)
        self.target = pygame.math.Vector2(target_pos)
        delta = self.target - self.start
        self.total_distance = max(1.0, delta.length())
        self.direction = delta.normalize() if delta.length_squared() > 0 else pygame.math.Vector2(1, 0)
        self.perp = pygame.math.Vector2(-self.direction.y, self.direction.x)

        self.travelled = 0.0
        self.base_position = self.start.copy()
        self.position = self.start.copy()
        self.has_impacted_target = False
        self.trail_positions = []
        self.trail_len = max(2, trail_len)
        self.spawn_time = pygame.time.get_ticks()

        angle = math.degrees(math.atan2(-self.direction.y, self.direction.x))
        dim_base = 32 if not self.is_tank else 42
        scaled = _scale_to_max_dim(EnemyThornProjectile._base_image, max(8, int(dim_base * sprite_scale)))
        self.image = pygame.transform.rotate(scaled, angle)
        self.rect = self.image.get_rect(center=(round(self.position.x), round(self.position.y)))
        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        if self.has_impacted_target:
            return

        remaining = self.total_distance - self.travelled
        step = min(self.speed, remaining)
        self.travelled += step

        self.base_position = self.start + (self.direction * self.travelled)
        wave_offset = self.perp * (math.sin(self.travelled * self.sine_frequency) * self.sine_amplitude)
        self.position = self.base_position + wave_offset
        self.rect.center = (round(self.position.x), round(self.position.y))

        self.trail_positions.append((self.position.x, self.position.y))
        if len(self.trail_positions) > self.trail_len:
            self.trail_positions.pop(0)

        if self.travelled >= self.total_distance:
            self.has_impacted_target = True

        # Safety timeout in case of any collision edge case.
        if pygame.time.get_ticks() - self.spawn_time > 3000:
            self.has_impacted_target = True

    def draw(self, surface):
        if self.trail_positions:
            count = len(self.trail_positions)
            for idx, point in enumerate(self.trail_positions):
                alpha = int(240 * ((idx + 1) / count))
                radius = max(3, int(3 + (idx / max(1, count - 1)) * 4))
                glow = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
                pygame.draw.circle(glow, (80, 255, 80, alpha), (radius * 2, radius * 2), radius)
                glow_rect = glow.get_rect(center=(round(point[0]), round(point[1])))
                surface.blit(glow, glow_rect)

        pulse = 0.65 + 0.35 * math.sin(pygame.time.get_ticks() * 0.02)
        core_radius = 5 if self.is_tank else 4
        core = pygame.Surface((24, 24), pygame.SRCALPHA)
        glow_alpha = int(120 + 80 * pulse)
        pygame.draw.circle(core, (255, 220, 120, glow_alpha), (12, 12), int(core_radius + 3 * pulse))
        core_rect = core.get_rect(center=self.rect.center)
        surface.blit(core, core_rect)

        surface.blit(self.image, self.rect)

