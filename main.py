import ctypes
try:
    ctypes.windll.user32.SetProcessDPIAware()
except:
    pass # Non-Windows systems don't need this

import pygame
import random
import math
from resource_utils import resource_path

VIRTUAL_RES = (1920, 1080)
global_offset = (0, 0)
global_scale = 1.0

# Patch pygame.mouse.get_pos to return scaled virtual coordinates
_original_get_pos = pygame.mouse.get_pos
def get_scaled_mouse_pos():
    m_x, m_y = _original_get_pos()
    virtual_x = (m_x - global_offset[0]) / global_scale
    virtual_y = (m_y - global_offset[1]) / global_scale
    return (int(virtual_x), int(virtual_y))
pygame.mouse.get_pos = get_scaled_mouse_pos

from collections import deque
from player import Player
from projectiles import Antibody, EnemyMuzzleFlash, EnemyThornProjectile, SplatterImpact
from structures import Organ
from enemies import Virus, Stalker, Tank, ExplosionParticle
from pickups import Pickup
from wavemanager import WaveManager
from boss import Boss
from ui_screens import get_font, draw_game_over, draw_xp_bar, CardSelectionMenu, init_fonts, GameInfoState, Button
from modifiers import recalculate_modifiers, roll_level_up_powerups, can_acquire_powerup
from soundmanager import SoundManager

# Game states
MAIN_MENU = 0
HOW_TO_PLAY = 1
DIRECTORY = 2
PLAYING = 3
GAME_OVER = 4
CINEMATIC_DEATH = 5
LEVEL_UP = 6
CENTER = pygame.math.Vector2(400, 300)

def grayscale_surface(surface):
    gray = pygame.Surface(surface.get_size())
    for x in range(surface.get_width()):
        for y in range(surface.get_height()):
            r, g, b, a = surface.get_at((x, y))
            avg = (r + g + b) // 3
            gray.set_at((x, y), (avg, avg, avg, a))
    return gray

def draw_cinematic_end(screen, score, mouse_pos, gameover_bg=None):
    if gameover_bg:
        screen.blit(gameover_bg, (0, 0))
    else:
        screen.fill((0, 0, 0))

    center_x = screen.get_width() // 2
    center_y = screen.get_height() // 2

    font_score = get_font(36)
    score_text = font_score.render(f"Final Score: {score}", True, (255, 255, 255))
    score_rect = score_text.get_rect(center=(center_x, center_y + 100))
    screen.blit(score_text, score_rect)

    temp_button = Button("RETURN TO MAIN MENU", 0, 0, 500, 64)
    temp_button.rect.center = (center_x, center_y + 180)
    temp_button.draw(screen)

    return temp_button.rect

def draw_eighth_note(surface, center, color):
    x, y = center
    # Note head
    pygame.draw.circle(surface, color, (x, y), 4)
    # Stem
    pygame.draw.line(surface, color, (x + 4, y), (x + 4, y - 12), 2)
    # Flag
    pygame.draw.line(surface, color, (x + 4, y - 12), (x + 8, y - 8), 2)

def draw_menu(screen, is_muted, buttons, mute_rect, mouse_pos, test_wave_button_rect=None, mainmenu_bg=None, mainmenu_logo=None):
    if mainmenu_bg:
        screen.blit(mainmenu_bg, (0, 0))
    else:
        screen.fill((0, 0, 0))

    if mainmenu_logo:
        current_time = pygame.time.get_ticks()
        base_y = screen.get_height() // 4  # Positioned at 1/4 down from top
        float_y = base_y + (12 * math.cos(current_time / 1200.0))

        # Opacity pulse using slow sine wave
        pulse_alpha = int((math.sin(current_time / 1200.0) * 0.5 + 0.5) * 100 + 155)  # between 155 and 255

        # We need to set_alpha on the image but to avoid changing original, use a copy
        logo_copy = mainmenu_logo.copy()
        logo_copy.set_alpha(pulse_alpha)

        logo_rect = logo_copy.get_rect(center=(screen.get_width() // 2, int(float_y)))
        screen.blit(logo_copy, logo_rect)
    else:
        font_title = get_font(72)
        title = font_title.render("IMMUNE SYSTEM", True, (255, 255, 255))
        title_rect = title.get_rect(center=(screen.get_width() // 2, max(90, screen.get_height() // 5)))
        screen.blit(title, title_rect)

    from ui_screens import Button

    font_button = get_font(36)
    for button in buttons:
        # Wrap button dictionary with the new class inline (or instantiate it per frame for now to keep code logic intact)
        temp_button = Button(button["text"], button["rect"].x, button["rect"].y, button["rect"].width, button["rect"].height)
        temp_button.draw(screen)

    # Test Wave 10 button (bottom-right corner)
    if test_wave_button_rect:
        color = (100, 50, 50) if test_wave_button_rect.collidepoint(mouse_pos) else (60, 30, 30)
        pygame.draw.rect(screen, color, test_wave_button_rect)
        pygame.draw.rect(screen, (150, 100, 100), test_wave_button_rect, 1)
        font_test = get_font(20)
        test_text = font_test.render("TEST: WAVE 10", True, (200, 100, 100))
        test_rect = test_text.get_rect(center=test_wave_button_rect.center)
        screen.blit(test_text, test_rect)

    # Mute button
    mute_color = (100, 100, 100) if mute_rect.collidepoint(mouse_pos) else (50, 50, 50)
    pygame.draw.rect(screen, mute_color, mute_rect)
    pygame.draw.rect(screen, (200, 200, 200), mute_rect, 2)
    draw_eighth_note(screen, mute_rect.center, (255, 255, 255))
    if is_muted:
        pygame.draw.line(screen, (255, 0, 0), mute_rect.topleft, mute_rect.bottomright, 3)
        pygame.draw.line(screen, (255, 0, 0), mute_rect.topright, mute_rect.bottomleft, 3)


def update_menu_layout(screen_rect, buttons, mute_rect, test_wave_button_rect=None):
    button_width = max(340, min(480, int(screen_rect.width * 0.5)))
    button_height = 64
    spacing = 80
    start_y = max(180, int(screen_rect.height * 0.33))
    x = (screen_rect.width - button_width) // 2

    for i, button in enumerate(buttons):
        button["rect"].update(x, start_y + i * spacing, button_width, button_height)

    mute_rect.update(screen_rect.width - 56, 16, 40, 40)

    if test_wave_button_rect is not None:
        test_wave_button_rect.update(screen_rect.width - 160, screen_rect.height - 50, 150, 40)


def draw_speed_boost_indicator(surface, player, current_time):
    if not hasattr(player, 'speed_boost_end_time') or current_time >= player.speed_boost_end_time:
        return

    remaining = max(0.0, (player.speed_boost_end_time - current_time) / 1000.0)
    stacks = getattr(player, 'speed_boost_stacks', 1)
    if not hasattr(draw_speed_boost_indicator, "_speed_icon"):
        try:
            icon = pygame.image.load(resource_path('sprites/speed.png')).convert_alpha()
            bbox = icon.get_bounding_rect()
            if bbox:
                icon = icon.subsurface(bbox).copy()
            draw_speed_boost_indicator._speed_icon = pygame.transform.smoothscale(icon, (28, 28))
        except pygame.error:
            fallback = pygame.Surface((28, 28), pygame.SRCALPHA)
            pygame.draw.circle(fallback, (255, 255, 255), (14, 14), 12, 2)
            draw_speed_boost_indicator._speed_icon = fallback

    font = get_font(20)
    label_text = f"SPD x{stacks} {remaining:.1f}s"
    label = font.render(label_text, True, (240, 240, 240))

    min_width = 210
    panel_width = max(min_width, 62 + label.get_width() + 14)
    panel = pygame.Rect(surface.get_width() - panel_width - 10, 10, panel_width, 46)
    pygame.draw.rect(surface, (28, 34, 36), panel, border_radius=6)

    icon_rect = draw_speed_boost_indicator._speed_icon.get_rect(midleft=(panel.x + 10, panel.centery))
    surface.blit(draw_speed_boost_indicator._speed_icon, icon_rect)

    label_rect = label.get_rect(midleft=(icon_rect.right + 10, panel.centery + 1))
    surface.blit(label, label_rect)


def set_display_mode(fullscreen_enabled, display_size=None):
    """Create a stable display surface for fullscreen/windowed switching."""
    if fullscreen_enabled:
        try:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN), True
        except pygame.error:
            fullscreen_enabled = False

    if display_size is None:
        display_size = (1600, 900)
    return pygame.display.set_mode(display_size, pygame.RESIZABLE), False


def fade_out_group(group, current_time, start_time, duration_ms):
    elapsed = current_time - start_time
    alpha = max(0, 255 - int(255 * (elapsed / duration_ms)))

    for sprite in list(group):
        if elapsed >= duration_ms:
            sprite.kill()
            continue
        if hasattr(sprite, 'image'):
            sprite.image.set_alpha(alpha)


def get_perimeter_spawn_point(screen_rect, recent_points=None, min_distance=140, max_attempts=20):
    margin = 12
    min_distance_sq = min_distance * min_distance
    candidate = (0, 0)

    for _ in range(max_attempts):
        side = random.choice(["top", "bottom", "left", "right"])
        if side == "top":
            candidate = (random.randint(0, screen_rect.width), -margin)
        elif side == "bottom":
            candidate = (random.randint(0, screen_rect.width), screen_rect.height + margin)
        elif side == "left":
            candidate = (-margin, random.randint(0, screen_rect.height))
        else:
            candidate = (screen_rect.width + margin, random.randint(0, screen_rect.height))

        if not recent_points:
            return candidate

        if all((candidate[0] - px) ** 2 + (candidate[1] - py) ** 2 >= min_distance_sq for px, py in recent_points):
            return candidate

    return candidate


def map_card_name_to_modifier_type(card_display_name):
    """
    Map CardSelectionMenu card display names to modifier type strings.

    Args:
        card_display_name: Card type_name from CardSelectionMenu (e.g., "Rapid Fire", "Pierce", "Well Nourished")

    Returns:
        Modifier type string (e.g., "rapid_fire", "pierce", "well_nourished")
    """
    # Backward-compatible helper: new menus already return powerup IDs directly.
    card_mapping = {
        "Rapid Fire": "rapid_fire",
        "Pierce": "pierce",
        "Well Nourished": "well_nourished",
    }
    return card_mapping.get(card_display_name, card_display_name)


def sync_organ_from_player_powerups(player, organ, refill=False):
    base_max = getattr(organ, 'base_max_health', 100)
    bonus = int(getattr(player, 'organ_max_health_bonus', 0))
    organ.max_health = max(1, base_max + bonus)

    if refill or getattr(player, 'refill_organ_on_upgrade', False):
        organ.health = organ.max_health
        if hasattr(player, 'refill_organ_on_upgrade'):
            player.refill_organ_on_upgrade = False
    else:
        organ.health = min(organ.health, organ.max_health)


def show_card_selection(screen, player):
    screen.fill((0, 0, 0))
    screen_rect = screen.get_rect()
    center_x = screen_rect.centerx
    center_y = screen_rect.centery

    font_title = get_font(72)
    title = font_title.render(f"LEVEL UP! (Level {player.level})", True, (0, 255, 0))
    title_rect = title.get_rect(center=(center_x, center_y - 150))
    screen.blit(title, title_rect)

    font_subtitle = get_font(32)
    subtitle = font_subtitle.render("Click a card to select:", True, (200, 200, 200))
    subtitle_rect = subtitle.get_rect(center=(center_x, center_y - 80))
    screen.blit(subtitle, subtitle_rect)

    card_width = 120
    card_height = 150
    card_padding = 40
    total_width = 3 * card_width + 2 * card_padding
    start_x = center_x - total_width // 2

    cards = [
        {"name": "FireRate+", "color": (255, 100, 0), "x": start_x, "y": center_y},
        {"name": "Speed+", "color": (100, 255, 100), "x": start_x + card_width + card_padding, "y": center_y},
        {"name": "Health+", "color": (255, 0, 100), "x": start_x + 2 * (card_width + card_padding), "y": center_y},
    ]

    card_rects = []
    for card in cards:
        rect = pygame.Rect(card["x"], card["y"], card_width, card_height)
        card_rects.append(rect)
        pygame.draw.rect(screen, card["color"], rect)
        pygame.draw.rect(screen, (255, 255, 255), rect, 3)
        card_text = get_font(24).render(card["name"], True, (255, 255, 255))
        text_rect = card_text.get_rect(center=rect.center)
        screen.blit(card_text, text_rect)

    return card_rects


_reticle_cursors = {}

def get_reticle_cursor(locked):
    if locked in _reticle_cursors:
        return _reticle_cursors[locked]

    color = (255, 50, 50, 220) if locked else (255, 255, 255, 170)
    reticle_surface = pygame.Surface((28, 28), pygame.SRCALPHA)
    center = (14, 14)

    pygame.draw.circle(reticle_surface, color, center, 8, 2)
    pygame.draw.line(reticle_surface, color, (14, 2), (14, 8), 2)
    pygame.draw.line(reticle_surface, color, (14, 20), (14, 26), 2)
    pygame.draw.line(reticle_surface, color, (2, 14), (8, 14), 2)
    pygame.draw.line(reticle_surface, color, (20, 14), (26, 14), 2)

    cursor = pygame.cursors.Cursor(center, reticle_surface)
    _reticle_cursors[locked] = cursor
    return cursor

def update_targeting_reticle(mouse_pos, enemies_group=None):
    locked = False
    if enemies_group:
        locked = any(enemy.rect.collidepoint(mouse_pos) for enemy in enemies_group if hasattr(enemy, 'rect'))

    cursor = get_reticle_cursor(locked)
    if pygame.mouse.get_cursor() != cursor:
        pygame.mouse.set_cursor(cursor)


def main():
    pygame.init()
    pygame.mixer.init()
    init_fonts()

    # Initialize SoundManager singleton
    SOUNDS_CONFIG = {
        'shoot': {'path': 'soundeffects/shoot.mp3', 'volume': 0.15},
        'enemy_hit': {'path': 'soundeffects/enemyhit.mp3', 'volume': 0.30},
        'enemy_death': {'path': 'soundeffects/enemydeath.mp3', 'volume': 0.45},
        'player_hit': {'path': 'soundeffects/playerhit.mp3', 'volume': 0.60},
        'player_death': {'path': 'soundeffects/playerdeath.mp3', 'volume': 0.90},
        'level_up': {'path': 'soundeffects/levelup.mp3', 'volume': 0.85},
        'pickup_collected': {'path': 'soundeffects/pickupcollected.mp3', 'volume': 0.65},
        'button_clicked': {'path': 'soundeffects/buttonclicked.mp3', 'volume': 0.50},
    }
    sound_manager = SoundManager.get_instance()
    sound_manager.__init__(SOUNDS_CONFIG, num_channels=16)

    pygame.mouse.set_visible(True)
    info = pygame.display.Info()
    desktop_sizes = pygame.display.get_desktop_sizes()
    desktop_size = desktop_sizes[0] if desktop_sizes else (1920, 1080)

    # Start in native fullscreen by default, then allow toggling to windowed mode.
    display_screen, fullscreen = set_display_mode(True)
    internal_surface = pygame.Surface(VIRTUAL_RES)
    screen = internal_surface

    pygame.display.set_caption('Immune System - Phase 1')
    clock = pygame.time.Clock()
    screen_rect = screen.get_rect()

    global CENTER
    CENTER = pygame.math.Vector2(screen_rect.center)

    font_score = get_font(32)
    score = 0
    game_start_time = 0
    last_second_score = 0
    rapid_fire_end_time = 0
    respawn_start_time = 0
    is_respawning = False
    cinematic_start = 0
    gray_screen = None
    music_switched = False
    despawn_start_time = 0
    despawn_duration_ms = 900
    rest_period_active = False
    rest_duration_ms = 5000
    rest_end_time = 0

    wave_manager = WaveManager()

    # Game state
    current_state = MAIN_MENU
    is_muted = False
    current_music = None
    level_up_pending = False
    card_menu = None
    game_info_state = None
    level_up_sound_channel = None  # Track level_up sound to pause music during playback
    music_paused_for_level_up = False
    music_pause_time = 0  # Track when music was paused to add timeout fallback
    boss_death_time = 0  # Track when boss dies to add 2-second delay before level-up

    # Menu elements
    buttons = [
        {"text": "PLAY", "rect": pygame.Rect(250, 250, 300, 50)},
        {"text": "HOW TO PLAY", "rect": pygame.Rect(250, 320, 300, 50)},
        {"text": "INFECTION DIRECTORY", "rect": pygame.Rect(250, 390, 300, 50)},
        {"text": "TOGGLE FULLSCREEN", "rect": pygame.Rect(250, 460, 300, 50)},
        {"text": "EXIT", "rect": pygame.Rect(250, 530, 300, 50)},
    ]
    mute_rect = pygame.Rect(750, 550, 40, 40)
    test_wave_button_rect = pygame.Rect(screen_rect.width - 160, screen_rect.height - 50, 150, 40)

    # Sub-menu button rects
    back_button_rect = pygame.Rect(0, 0, 160, 54)
    back_button_rect.center = (screen_rect.centerx, min(screen_rect.height - 60, screen_rect.centery + 180))
    return_button_rect = pygame.Rect(0, 0, 280, 56)
    return_button_rect.center = (screen_rect.centerx, screen_rect.centery + 70)
    update_menu_layout(screen_rect, buttons, mute_rect, test_wave_button_rect)

    # Initialize game objects
    organ = Organ(screen_rect)
    organ.rect.center = CENTER
    player = Player(screen_rect)
    player.rect.center = (int(CENTER.x + 120), int(CENTER.y))
    player_group = pygame.sprite.Group(player)
    all_sprites = pygame.sprite.Group(player)
    projectiles_group = pygame.sprite.Group()
    virus_group = pygame.sprite.Group()
    boss_group = pygame.sprite.Group()
    boss_projectiles_group = pygame.sprite.Group()
    particles_group = pygame.sprite.Group()
    enemy_thorn_group = pygame.sprite.Group()
    enemy_attack_fx_group = pygame.sprite.Group()
    enemy_stain_group = pygame.sprite.Group()
    pickup_group = pygame.sprite.Group()
    recent_spawn_points = deque(maxlen=10)

    # Load and scale background for play stage
    raw_background = pygame.image.load(resource_path('sprites/background.png')).convert_alpha()
    background = pygame.transform.scale(raw_background, screen_rect.size)

    # Load and scale main menu background
    raw_mainmenu_bg = pygame.image.load(resource_path('sprites/mainmenu.png')).convert_alpha()
    mainmenu_bg = pygame.transform.scale(raw_mainmenu_bg, screen_rect.size)

    # Load and scale game over background
    raw_gameover_bg = pygame.image.load(resource_path('sprites/gameover.png')).convert_alpha()
    gameover_bg = pygame.transform.scale(raw_gameover_bg, screen_rect.size)

    # Load main menu logo
    raw_mainmenu_logo = pygame.image.load(resource_path('sprites/logo.png')).convert_alpha()
    # scale logo initially (25% of screen width)
    target_w = min(int(screen_rect.width * 0.25), raw_mainmenu_logo.get_width())
    target_h = int((target_w / raw_mainmenu_logo.get_width()) * raw_mainmenu_logo.get_height())
    mainmenu_logo = pygame.transform.smoothscale(raw_mainmenu_logo, (target_w, target_h))

    # Boss wave tracking
    boss_theme_playing = False

    # Timer for spawning viruses
    SPAWN_VIRUS = pygame.USEREVENT + 1
    pygame.time.set_timer(SPAWN_VIRUS, 1000)

    running = True
    while running:
        current_time = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                if not fullscreen:
                    display_screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                screen_rect = screen.get_rect()
                CENTER = pygame.math.Vector2(screen_rect.center)
                player.screen_rect = screen_rect
                update_menu_layout(screen_rect, buttons, mute_rect, test_wave_button_rect)
                # Rescale backgrounds to new screen size
                background = pygame.transform.scale(raw_background, screen_rect.size)
                mainmenu_bg = pygame.transform.scale(raw_mainmenu_bg, screen_rect.size)
                gameover_bg = pygame.transform.scale(raw_gameover_bg, screen_rect.size)

                # Rescale main menu logo to maintaining aspect ratio (target max width 25%)
                target_w = min(int(screen_rect.width * 0.25), raw_mainmenu_logo.get_width())
                target_h = int((target_w / raw_mainmenu_logo.get_width()) * raw_mainmenu_logo.get_height())
                mainmenu_logo = pygame.transform.smoothscale(raw_mainmenu_logo, (target_w, target_h))

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                if current_state == MAIN_MENU:
                    for button in buttons:
                        if button["rect"].collidepoint(mouse_pos):
                            sound_manager.play('button_clicked')
                            if button["text"] == "PLAY":
                                current_state = PLAYING
                                # Reset game state
                                organ.max_health = getattr(organ, 'base_max_health', 100)
                                organ.health = organ.max_health
                                player.rect.center = (int(CENTER.x + 120), int(CENTER.y))
                                virus_group.empty()
                                projectiles_group.empty()
                                boss_group.empty()
                                boss_projectiles_group.empty()
                                particles_group.empty()
                                enemy_thorn_group.empty()
                                enemy_attack_fx_group.empty()
                                enemy_stain_group.empty()
                                pickup_group.empty()
                                recent_spawn_points.clear()
                                score = 0
                                player.health = 100
                                player.shield_hits = 0
                                player.fire_rate_multiplier = 1.0
                                # Reset player progression and buffs
                                player.level = 1
                                player.current_xp = 0
                                player.xp_to_next_level = 100
                                player.size = 1.0
                                player.base_speed = 5.8
                                player.base_max_health = 100
                                player.base_size = 1.0
                                player.max_health = 100
                                player.speed = 5.8
                                player.modifiers = []
                                player.active_cards = []
                                player.fire_rate_multiplier = 1.0 # Ensure base stat is fully reset

                                # Added explicit recalculate call to purge buff states properly
                                from modifiers import recalculate_modifiers
                                recalculate_modifiers(player)
                                sync_organ_from_player_powerups(player, organ, refill=True)

                                game_start_time = pygame.time.get_ticks()
                                last_second_score = 0
                                rapid_fire_end_time = 0
                                is_respawning = False
                                respawn_start_time = 0
                                rest_period_active = False
                                rest_end_time = 0
                                boss_theme_playing = False
                                boss_death_time = 0
                                music_pause_time = 0
                                wave_manager = WaveManager()
                                wave_manager.start_next_wave()
                                pygame.time.set_timer(SPAWN_VIRUS, wave_manager.get_spawn_delay())
                            elif button["text"] == "HOW TO PLAY":
                                current_state = HOW_TO_PLAY
                                game_info_state = GameInfoState('HOW_TO_PLAY', screen_rect)
                            elif button["text"] == "INFECTION DIRECTORY":
                                current_state = DIRECTORY
                                game_info_state = GameInfoState('DIRECTORY', screen_rect)
                            elif button["text"] == "TOGGLE FULLSCREEN":
                                if fullscreen:
                                    window_width = min(1600, desktop_size[0])
                                    window_height = min(900, desktop_size[1])
                                    display_screen, fullscreen = set_display_mode(False, (window_width, window_height))
                                else:
                                    display_screen, fullscreen = set_display_mode(True)

                                screen_rect = screen.get_rect()
                                CENTER = pygame.math.Vector2(screen_rect.center)
                                player.screen_rect = screen_rect
                                update_menu_layout(screen_rect, buttons, mute_rect, test_wave_button_rect)
                            elif button["text"] == "EXIT":
                                running = False
                    if mute_rect.collidepoint(mouse_pos):
                        is_muted = not is_muted
                        pygame.mixer.music.set_volume(0.0 if is_muted else 0.5)
                    if test_wave_button_rect.collidepoint(mouse_pos):
                        sound_manager.play('button_clicked')
                        current_state = PLAYING
                        # Reset game state
                        organ.max_health = getattr(organ, 'base_max_health', 100)
                        organ.health = organ.max_health
                        player.rect.center = (int(CENTER.x + 120), int(CENTER.y))
                        virus_group.empty()
                        projectiles_group.empty()
                        boss_group.empty()
                        boss_projectiles_group.empty()
                        particles_group.empty()
                        enemy_thorn_group.empty()
                        enemy_attack_fx_group.empty()
                        enemy_stain_group.empty()
                        pickup_group.empty()
                        recent_spawn_points.clear()
                        score = 0
                        player.health = 100
                        player.shield_hits = 0
                        player.fire_rate_multiplier = 1.0
                        player.level = 1
                        player.current_xp = 0
                        player.xp_to_next_level = 100
                        player.size = 1.0
                        player.base_speed = 5.8
                        player.base_max_health = 100
                        player.base_size = 1.0
                        player.max_health = 100
                        player.speed = 5.8
                        player.modifiers = []
                        player.active_cards = []
                        player.fire_rate_multiplier = 1.0 # Ensure base stat is fully reset

                        # Added explicit recalculate call to purge buff states properly
                        from modifiers import recalculate_modifiers
                        recalculate_modifiers(player)
                        sync_organ_from_player_powerups(player, organ, refill=True)

                        game_start_time = pygame.time.get_ticks()
                        last_second_score = 0
                        rapid_fire_end_time = 0
                        is_respawning = False
                        respawn_start_time = 0
                        rest_period_active = False
                        rest_end_time = 0
                        boss_theme_playing = False
                        boss_death_time = 0
                        music_pause_time = 0
                        # Skip to Wave 10 with player upgrades
                        player.level = 5
                        wave_manager = WaveManager()
                        wave_manager.current_wave = 10
                        wave_manager.is_boss_wave = True
                        wave_manager.boss_wave_start_time = pygame.time.get_ticks()
                        wave_manager.wave_active = True
                        pygame.time.set_timer(SPAWN_VIRUS, wave_manager.get_spawn_delay())
                elif current_state in [HOW_TO_PLAY, DIRECTORY, GAME_OVER]:
                    if current_state == HOW_TO_PLAY and game_info_state and game_info_state.back_button.rect.collidepoint(mouse_pos):
                        sound_manager.play('button_clicked')
                        current_state = MAIN_MENU
                        game_info_state = None
                    elif current_state == DIRECTORY and game_info_state and game_info_state.back_button.rect.collidepoint(mouse_pos):
                        sound_manager.play('button_clicked')
                        current_state = MAIN_MENU
                        game_info_state = None
                    elif current_state == GAME_OVER and return_button_rect.collidepoint(mouse_pos):
                        sound_manager.play('button_clicked')
                        current_state = MAIN_MENU
                elif current_state == LEVEL_UP:
                    if card_menu is None:
                        rolled_powerups = roll_level_up_powerups(player, count=3)
                        if not rolled_powerups:
                            current_state = PLAYING
                            level_up_pending = False
                            card_menu = None
                            continue
                        card_menu = CardSelectionMenu(screen, player, rolled_powerups)

                    clicked_powerup_id = card_menu.handle_click(mouse_pos)
                    if clicked_powerup_id:
                        sound_manager.play('button_clicked')

                        if can_acquire_powerup(player, clicked_powerup_id):
                            # Add to active cards and recalculate all modifiers.
                            # Effects apply only to the player because modifiers are applied on `player`.
                            player.active_cards.append(clicked_powerup_id)
                            recalculate_modifiers(player)
                            sync_organ_from_player_powerups(player, organ)
                            print(f"{clicked_powerup_id} selected! Active cards: {player.active_cards}")

                        current_state = PLAYING
                        level_up_pending = False
                        card_menu = None
                elif current_state == CINEMATIC_DEATH:
                    elapsed = current_time - cinematic_start
                    if elapsed > 5000 and event.type == pygame.MOUSEBUTTONDOWN:
                        button_rect = pygame.Rect(0, 0, 400, 64)
                        button_rect.center = (screen_rect.width // 2, screen_rect.height // 2 + 180)
                        if button_rect.collidepoint(mouse_pos):
                            sound_manager.play('button_clicked')
                            current_state = MAIN_MENU
            elif event.type == SPAWN_VIRUS and current_state == PLAYING:
                if not rest_period_active and not wave_manager.is_boss_wave and wave_manager.enemies_spawned < wave_manager.wave_budget:
                    total_alive = len(virus_group) + len(boss_group)
                    alive_cap = wave_manager.get_alive_enemy_cap()
                    remaining_budget = wave_manager.wave_budget - wave_manager.enemies_spawned
                    available_slots = max(0, alive_cap - total_alive)
                    spawn_count = min(
                        wave_manager.get_spawn_batch_size(),
                        remaining_budget,
                        available_slots,
                    )

                    if spawn_count > 0:
                        enemy_cls_map = {
                            "Virus": Virus,
                            "Stalker": Stalker,
                            "Tank": Tank,
                        }

                        for _ in range(spawn_count):
                            x, y = get_perimeter_spawn_point(screen_rect, recent_spawn_points)
                            recent_spawn_points.append((x, y))

                            enemy_name = wave_manager.get_enemy_type()
                            enemy_cls = enemy_cls_map[enemy_name]

                            target = player.rect.center if enemy_cls == Stalker else organ.rect.center
                            enemy = enemy_cls(x, y, target)
                            virus_group.add(enemy)
                            all_sprites.add(enemy)
                            wave_manager.mark_enemy_spawned()

        mouse_pos = pygame.mouse.get_pos()

        # Music switching
        if current_state in [HOW_TO_PLAY, DIRECTORY] and current_music != 'howtoplay':
            if current_music is not None:
                pygame.mixer.music.fadeout(1000)
            try:
                pygame.mixer.music.load(resource_path('soundtrack/howtoplay.mp3'))
                pygame.mixer.music.play(-1, 0.0, 1000)  # loops=-1, start=0, fade_ms=1000
                pygame.mixer.music.set_volume(0.5 if not is_muted else 0.0)
            except pygame.error:
                print('Unable to load howtoplay soundtrack.')
            current_music = 'howtoplay'
        elif current_state in [MAIN_MENU, GAME_OVER] and current_music != 'menu':
            if current_music is not None:
                pygame.mixer.music.fadeout(1000)
            try:
                pygame.mixer.music.load(resource_path('soundtrack/menusoundtrack.mp3'))
                pygame.mixer.music.play(-1, 0.0, 1000)  # loops=-1, start=0, fade_ms=1000
                pygame.mixer.music.set_volume(0.5 if not is_muted else 0.0)
            except pygame.error:
                print('Unable to load menu soundtrack.')
            current_music = 'menu'
        # Boss wave music takes priority
        if current_state == PLAYING and wave_manager.is_boss_wave and current_music != 'boss':
            if current_music is not None:
                pygame.mixer.music.fadeout(1000)
            try:
                pygame.mixer.music.load(resource_path('soundtrack/bossmusic.mp3'))
                pygame.mixer.music.play(-1, 0.0, 1000)  # loops=-1, start=0, fade_ms=1000
                pygame.mixer.music.set_volume(0.5 if not is_muted else 0.0)
            except pygame.error:
                print('Unable to load bossmusic soundtrack.')
            current_music = 'boss'
        elif current_state == PLAYING and not wave_manager.is_boss_wave and current_music != 'fight':
            if current_music is not None:
                pygame.mixer.music.fadeout(1000)
            try:
                pygame.mixer.music.load(resource_path('soundtrack/fightsoundtrack.mp3'))
                pygame.mixer.music.play(-1, 0.0, 1000)  # loops=-1, start=0, fade_ms=1000
                pygame.mixer.music.set_volume(0.5 if not is_muted else 0.0)
            except pygame.error:
                print('Unable to load fight soundtrack.')
            current_music = 'fight'

        # Resume music after level_up sound finishes (runs every frame regardless of state)
        if music_paused_for_level_up:
            should_resume = False

            # Primary: Resume when level-up sound finishes
            if level_up_sound_channel and not level_up_sound_channel.get_busy():
                should_resume = True

            # Fallback: Resume after 2 seconds if sound never played (channel is None)
            if not level_up_sound_channel and music_pause_time > 0:
                if current_time - music_pause_time >= 2000:
                    should_resume = True

            if should_resume:
                pygame.mixer.music.unpause()
                music_paused_for_level_up = False
                level_up_sound_channel = None
                music_pause_time = 0

        # Clear the internal frame first so alpha backgrounds cannot leave ghost artifacts.
        screen.fill((0, 0, 0))

        if current_state == MAIN_MENU:
            # Pulse the organ quietly in menu background
            organ.update(current_state, False)
            draw_menu(screen, is_muted, buttons, mute_rect, mouse_pos, test_wave_button_rect, mainmenu_bg, mainmenu_logo)
        elif current_state == HOW_TO_PLAY:
            if game_info_state:
                game_info_state.draw(screen, mouse_pos)
        elif current_state == DIRECTORY:
            if game_info_state:
                game_info_state.draw(screen, mouse_pos)
        elif current_state == LEVEL_UP:
            if card_menu is None:
                rolled_powerups = roll_level_up_powerups(player, count=3)
                if not rolled_powerups:
                    current_state = PLAYING
                    level_up_pending = False
                    card_menu = None
                    continue
                card_menu = CardSelectionMenu(screen, player, rolled_powerups)

            # Update and draw card menu
            card_menu.update(0)  # Update uses internal timing based on menu_open_time
            card_menu.draw()
        elif current_state == PLAYING:
            current_time = pygame.time.get_ticks()
            organ.update(current_state, getattr(wave_manager, 'is_boss_wave', False))
            player_group.update(organ, is_respawning)
            projectiles_group.update(virus_group)
            virus_group.update(current_time, player, organ)
            pickup_group.update()
            particles_group.update()
            enemy_thorn_group.update()
            enemy_attack_fx_group.update()
            enemy_stain_group.update()

            # Stalkers emit boss-style projectiles; collect them into the shared hostile projectile group.
            for enemy in virus_group:
                if isinstance(enemy, Stalker) and hasattr(enemy, 'projectiles'):
                    boss_projectiles_group.add(enemy.projectiles)

            # Boss wave updates
            if wave_manager.is_boss_wave:
                # Spawn boss after 8-second delay
                if wave_manager.should_spawn_boss():
                    spawn_positions = wave_manager.get_boss_spawn_info(screen_rect)
                    for x, y in spawn_positions:
                        boss = Boss(x, y, screen_rect, organ=organ)

                        if wave_manager.current_wave >= 20:
                            W, H = screen_rect.width, screen_rect.height
                            if x < W // 2:
                                boss.last_chase_direction = pygame.math.Vector2(0.5, 1).normalize()
                            else:
                                boss.last_chase_direction = pygame.math.Vector2(-0.5, -1).normalize()

                        boss_group.add(boss)
                        all_sprites.add(boss)

                # Update bosses and collect their projectiles
                for boss in boss_group:
                    boss.update(current_time, player, organ)
                    boss_projectiles_group.add(boss.projectiles)
                    # Add spawned enemies to virus_group
                    virus_group.add(boss.spawned_enemies)
                    all_sprites.add(boss.spawned_enemies)

            boss_projectiles_group.update()

            # Pickup buff expiry
            if hasattr(player, 'speed_boost_end_time') and current_time >= player.speed_boost_end_time:
                player.speed = getattr(player, 'base_speed', player.speed)
                delattr(player, 'speed_boost_end_time')
                if hasattr(player, 'speed_boost_stacks'):
                    delattr(player, 'speed_boost_stacks')

            # Scoring by survival time
            if game_start_time:
                elapsed_seconds = (current_time - game_start_time) // 1000
                if elapsed_seconds > last_second_score:
                    score += elapsed_seconds - last_second_score
                    last_second_score = elapsed_seconds

            # Wave progression and rest phase
            if not rest_period_active:
                total_enemies_alive = len(virus_group) + len(boss_group)
                if wave_manager.is_boss_wave:
                    wave_done = wave_manager.boss_spawned and total_enemies_alive == 0
                else:
                    wave_done = (
                        wave_manager.enemies_spawned >= wave_manager.wave_budget
                        and total_enemies_alive == 0
                    )
                if wave_done:
                    rest_period_active = True
                    rest_end_time = current_time + rest_duration_ms
                    organ.health = organ.max_health
                    player.health = getattr(player, 'max_health', player.health)
                    boss_theme_playing = False  # Reset for next normal wave
            elif current_time >= rest_end_time:
                rest_period_active = False
                wave_manager.start_next_wave()
                pygame.time.set_timer(SPAWN_VIRUS, wave_manager.get_spawn_delay())

            # Boss death level-up delay: Wait 2 seconds after boss dies to show death animation
            if boss_death_time > 0 and current_time - boss_death_time >= 2000:
                # Play level-up sound IMMEDIATELY before state change
                level_up_sound_channel = sound_manager.play('level_up')
                print('Level Up Sound Triggered')
                print(f"[BOSS DEATH] Level-up sound channel: {level_up_sound_channel}")

                # Stop all other sound channels except UI channel (7) to avoid overlap (but not music)
                num_channels = pygame.mixer.get_num_channels()
                for i in range(num_channels):
                    if i != 7:  # UI channel is 7
                        ch = pygame.mixer.Channel(i)
                        if ch.get_busy():
                            print(f"Stopping channel {i}")
                            ch.stop()
                pygame.mixer.music.pause()
                music_paused_for_level_up = True
                music_pause_time = current_time  # Track when music was paused for timeout fallback

                # NOW change state AFTER sound is playing
                level_up_pending = True
                current_state = LEVEL_UP
                boss_death_time = 0  # Reset the timer

            # Collisions
            hits = pygame.sprite.groupcollide(projectiles_group, virus_group, False, False, pygame.sprite.collide_mask)
            projectiles_to_remove = set()  # Track projectiles that should be removed

            for projectile, enemies in hits.items():
                hit_this_frame = False  # Track if this projectile hit anyone this frame

                for enemy in enemies:
                    # Use mask collision result directly instead of distance check
                    if True:
                        # Get projectile damage (default 1)
                        projectile_damage = getattr(projectile, 'damage', 1)
                        enemy_health_before = enemy.health

                        # Apply damage if enemy is not already dead
                        if enemy.take_damage(projectile_damage, pickup_group, all_sprites):
                            # Enemy died
                            sound_manager.play('enemy_death')
                            enemy_color = getattr(enemy, 'primary_color', (255, 255, 255))
                            for i in range(8):
                                angle = i * 45
                                direction = pygame.math.Vector2(1, 0).rotate(angle)
                                particle = ExplosionParticle(enemy.rect.centerx, enemy.rect.centery, direction, enemy_color)
                                particles_group.add(particle)
                            enemy.kill()
                            score += 10
                            xp_reward = 0
                            if isinstance(enemy, Virus):
                                xp_reward = 10
                            elif isinstance(enemy, Stalker):
                                xp_reward = 15
                            elif isinstance(enemy, Tank):
                                xp_reward = 30
                            if xp_reward > 0 and player.gain_xp(xp_reward):
                                # Play level-up sound IMMEDIATELY before state change
                                level_up_sound_channel = sound_manager.play('level_up')
                                print('Level Up Sound Triggered')
                                print(f"[ENEMY KILL] Level-up sound channel: {level_up_sound_channel}")

                                # Stop all other sound channels except UI channel (7) to avoid overlap (but not music)
                                num_channels = pygame.mixer.get_num_channels()
                                for i in range(num_channels):
                                    if i != 7:  # UI channel is 7
                                        ch = pygame.mixer.Channel(i)
                                        if ch.get_busy():
                                            print(f"Stopping channel {i}")
                                            ch.stop()
                                pygame.mixer.music.pause()
                                music_paused_for_level_up = True
                                music_pause_time = current_time  # Track when music was paused for timeout fallback

                                # NOW change state AFTER sound is playing
                                level_up_pending = True
                                current_state = LEVEL_UP
                        else:
                            # Enemy hit but not killed
                            sound_manager.play('enemy_hit')

                        hit_this_frame = True

                # Handle pierce logic after checking all collisions for this projectile
                if hit_this_frame:
                    pierce_count = getattr(projectile, 'pierce_count', 0)
                    if pierce_count <= 0:
                        # No pierce: projectile dies after first hit
                        projectiles_to_remove.add(projectile)
                    else:
                        # Has pierce: decrement and continue (unless pierce reaches -1)
                        projectile.pierce_count -= 1
                        if projectile.pierce_count < 0:
                            projectiles_to_remove.add(projectile)

            # Remove projectiles that have exhausted their pierce
            for projectile in projectiles_to_remove:
                projectile.kill()

            # Player-enemy collision (contact damage)
            player_hit_enemies = pygame.sprite.spritecollide(player, virus_group, False, pygame.sprite.collide_mask)
            for enemy in player_hit_enemies:
                # Try to apply damage to player (handles invulnerability and cooldown)
                if player.try_take_hit(current_time, damage=10):
                    sound_manager.play('player_hit')

            # Boss projectile collision with player
            boss_projectile_hits = pygame.sprite.spritecollide(player, boss_projectiles_group, True, pygame.sprite.collide_mask)
            for projectile in boss_projectile_hits:
                if player.try_take_hit(current_time, damage=getattr(projectile, 'damage', 15)):
                    sound_manager.play('player_hit')

            # Boss contact damage (boss touching player)
            if wave_manager.is_boss_wave:
                boss_contact_hits = pygame.sprite.spritecollide(player, boss_group, False, pygame.sprite.collide_mask)
                for boss in boss_contact_hits:
                    # Boss deals significant damage on contact
                    if player.try_take_hit(current_time, damage=30):
                        sound_manager.play('player_hit')

            # Antibody collision with bosses
            if wave_manager.is_boss_wave:
                antibody_boss_hits = pygame.sprite.groupcollide(projectiles_group, boss_group, False, False, pygame.sprite.collide_mask)
                boss_projectiles_to_remove = set()
                for projectile, bosses in antibody_boss_hits.items():
                    hit_unshielded_boss = False
                    for boss in bosses:
                        projectile_damage = getattr(projectile, 'damage', 1)

                        hit_unshielded_boss = True
                        # Damage the boss directly through its hit handler.
                        boss.take_damage(projectile_damage)
                        sound_manager.play('enemy_hit')

                        # Check if boss died
                        if boss.health <= 0:
                            sound_manager.play('enemy_death')
                            boss_color = getattr(boss, 'primary_color', (255, 0, 0))
                            for i in range(12):
                                angle = i * 30
                                direction = pygame.math.Vector2(1, 0).rotate(angle)
                                particle = ExplosionParticle(boss.rect.centerx, boss.rect.centery, direction, boss_color)
                                particles_group.add(particle)
                            boss.kill()
                            score += 100
                            # Give significant XP for boss kill
                            if player.gain_xp(150):
                                boss_death_time = current_time  # Mark boss death time

                        # Single boss hit per frame is enough for this projectile.
                        break

                    if hit_unshielded_boss:
                        pierce_count = getattr(projectile, 'pierce_count', 0)
                        if pierce_count >= 1:
                            projectile.pierce_count -= 1
                        else:
                            boss_projectiles_to_remove.add(projectile)

                for projectile in boss_projectiles_to_remove:
                    projectile.kill()

            # Player pickup collection
            hits = pygame.sprite.spritecollide(player, pickup_group, True, pygame.sprite.collide_mask)
            for hit in hits:
                hit.apply_effect(player)
                sound_manager.play('pickup_collected')
                print(f"Pickup collected: {hit.type_name}")
                score += 100

            # Shoot projectiles
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE] and current_state == PLAYING:
                if getattr(player, 'scattershot_enabled', False):
                    antibodies = Antibody.fire_scattershot_from_player(player, screen_rect, virus_group)
                    if antibodies:
                        projectiles_group.add(*antibodies)
                else:
                    antibody = Antibody.fire_from_player(player, screen_rect, virus_group)
                    if antibody is not None:
                        projectiles_group.add(antibody)

            # Virus damage (disabled during level-up menus)
            if current_state != LEVEL_UP:
                for virus in virus_group:
                    if virus.damage_organ:
                        virus.damage_organ = False

                        if isinstance(virus, Stalker):
                            continue

                        target_pos = pygame.math.Vector2(organ.rect.center)
                        virus_pos = pygame.math.Vector2(virus.rect.center)
                        shot_dir = target_pos - virus_pos
                        if shot_dir.length_squared() == 0:
                            shot_dir = pygame.math.Vector2(1, 0)
                        else:
                            shot_dir = shot_dir.normalize()

                        muzzle_pos = virus_pos + shot_dir * max(10, virus.rect.width * 0.48)
                        is_tank = isinstance(virus, Tank)

                        enemy_attack_fx_group.add(
                            EnemyMuzzleFlash(
                                muzzle_pos,
                                target_pos,
                                scale=2.4 if is_tank else 1.3,
                                lifetime_ms=200,
                            )
                        )

                        enemy_thorn_group.add(
                            EnemyThornProjectile(
                                muzzle_pos,
                                target_pos,
                                attacker=virus,
                                speed=4.1 if is_tank else 8.5,
                                damage=10,
                                sine_amplitude=0.0 if is_tank else 8.0,
                                sine_frequency=0.28,
                                sprite_scale=1.25 if is_tank else 1.1,
                                is_tank=is_tank,
                            )
                        )

            thorn_hits = pygame.sprite.spritecollide(organ, enemy_thorn_group, False, pygame.sprite.collide_mask)
            pending_target_hits = [thorn for thorn in enemy_thorn_group if thorn.has_impacted_target]

            for thorn in set(thorn_hits + pending_target_hits):
                if not thorn.alive():
                    continue
                if current_state == LEVEL_UP:
                    # Prevent any organ damage while the level-up screen is active.
                    thorn.kill()
                    continue

                organ.health -= getattr(thorn, 'damage', 10)
                enemy_attack_fx_group.add(
                    SplatterImpact(
                        thorn.rect.center,
                        persist_group=enemy_stain_group,
                        attacker=getattr(thorn, 'attacker', None),
                        scale=1.7 if getattr(thorn, 'is_tank', False) else 1.2,
                    )
                )
                thorn.kill()

            # Remove projectiles that hit the organ
            pygame.sprite.spritecollide(organ, projectiles_group, True, pygame.sprite.collide_mask)

            # Respawn logic
            if player.health <= 0 and not is_respawning:
                sound_manager.stop_all()  # Cut all other sounds immediately
                sound_manager.play('player_death')
                is_respawning = True
                respawn_start_time = current_time

            if is_respawning:
                if current_time - respawn_start_time >= 2000:
                    player.health = 100
                    player.rect.center = (int(CENTER.x + 120), int(CENTER.y))
                    is_respawning = False

            if organ.health <= 0:
                organ.health = 0  # Ensure health bar shows 0
                organ.draw_health_bar(screen)  # Redraw with 0 health
                current_state = CINEMATIC_DEATH
                cinematic_start = current_time
                despawn_start_time = current_time
                gray_screen = None
                pygame.mixer.music.fadeout(1000)  # Fade out fight music
                music_switched = False

            # Draw
            screen.blit(background, (0, 0))
            if player.is_visible(current_time):
                player_group.draw(screen)
            # Draw player health bar
            player.draw_health_bar(screen)
            pickup_group.draw(screen)

            for projectile in projectiles_group:
                if hasattr(projectile, 'draw'):
                    projectile.draw(screen)
                else:
                    screen.blit(projectile.image, projectile.rect)

            screen.blit(organ.image, organ.rect)
            enemy_stain_group.draw(screen)
            organ.draw_health_bar(screen)
            virus_group.draw(screen)
            boss_projectiles_group.draw(screen)
            for thorn in enemy_thorn_group:
                if hasattr(thorn, 'draw'):
                    thorn.draw(screen)
                else:
                    screen.blit(thorn.image, thorn.rect)
            enemy_attack_fx_group.draw(screen)
            particles_group.draw(screen)
            for virus in virus_group:
                virus.draw_sweep(screen)

            # Draw bosses
            for boss in boss_group:
                boss.draw(screen)

            score_text = font_score.render(f"Score: {score}", True, (255, 255, 255))
            screen.blit(score_text, (10, 10))

            wave_text = font_score.render(f"WAVE {wave_manager.current_wave}", True, (255, 255, 255))
            wave_rect = wave_text.get_rect(midtop=(screen_rect.width // 2, 46))
            screen.blit(wave_text, wave_rect)

            # Boss wave countdown UI
            if wave_manager.is_boss_wave and not wave_manager.boss_spawned:
                remaining_ms = wave_manager.get_boss_countdown_ms()
                remaining_sec = max(0, (remaining_ms + 999) // 1000)  # Round up to nearest second

                # Draw "SYSTEMIC DANGER IMMINENT" message (moved up, less bold, better color)
                font_threat = get_font(56, bold=False)  # Smaller, less bold
                threat_text = font_threat.render("SYSTEMIC DANGER IMMINENT", True, (255, 120, 0)) # Readable orange-red
                # Positioned well above the heart (organ occupies center to roughly -175 up)
                threat_rect = threat_text.get_rect(center=(screen_rect.width // 2, screen_rect.height // 2 - 220))
                screen.blit(threat_text, threat_rect)

                # Draw countdown timer
                font_countdown = get_font(72, bold=False)
                countdown_text = font_countdown.render(str(remaining_sec), True, (255, 200, 50))
                countdown_rect = countdown_text.get_rect(center=(screen_rect.width // 2, screen_rect.height // 2 - 160))
                screen.blit(countdown_text, countdown_rect)

            draw_speed_boost_indicator(screen, player, current_time)
            draw_xp_bar(screen, player)

            if rest_period_active:
                rest_font = get_font(48)
                clear_text = rest_font.render("WAVE CLEAR", True, (255, 255, 255))
                countdown = max(0.0, (rest_end_time - current_time) / 1000.0)
                timer_text = font_score.render(f"Next wave in {countdown:.1f}s", True, (255, 255, 255))
                clear_rect = clear_text.get_rect(center=(screen_rect.width // 2, screen_rect.height // 2 - 25))
                timer_rect = timer_text.get_rect(center=(screen_rect.width // 2, screen_rect.height // 2 + 20))
                screen.blit(clear_text, clear_rect)
                screen.blit(timer_text, timer_rect)

            if is_respawning:
                remaining = 2 - (current_time - respawn_start_time) / 1000
                respawn_text = font_score.render(f"Respawning in {remaining:.1f} seconds", True, (255, 255, 255))
                respawn_rect = respawn_text.get_rect(center=(organ.rect.centerx, organ.rect.top - 40))
                screen.blit(respawn_text, respawn_rect)
        elif current_state == CINEMATIC_DEATH:
            elapsed = current_time - cinematic_start
            fade_out_group(projectiles_group, current_time, despawn_start_time, despawn_duration_ms)
            fade_out_group(pickup_group, current_time, despawn_start_time, despawn_duration_ms)

            if gray_screen is None:
                # Render a live frame during despawn so bullet/pickup fade is visible.
                screen.blit(background, (0, 0))
                if player.is_visible(current_time):
                    player_group.draw(screen)
                player.draw_health_bar(screen)
                pickup_group.draw(screen)

                for projectile in projectiles_group:
                    if hasattr(projectile, 'draw'):
                        projectile.draw(screen)
                    else:
                        screen.blit(projectile.image, projectile.rect)

                screen.blit(organ.image, organ.rect)
                enemy_stain_group.draw(screen)
                organ.draw_health_bar(screen)
                virus_group.draw(screen)
                for thorn in enemy_thorn_group:
                    if hasattr(thorn, 'draw'):
                        thorn.draw(screen)
                    else:
                        screen.blit(thorn.image, thorn.rect)
                enemy_attack_fx_group.draw(screen)
                particles_group.draw(screen)
                for virus in virus_group:
                    virus.draw_sweep(screen)

                score_text = font_score.render(f"Score: {score}", True, (255, 255, 255))
                screen.blit(score_text, (10, 10))
                draw_speed_boost_indicator(screen, player, current_time)

                if current_time - despawn_start_time >= despawn_duration_ms:
                    gray_screen = grayscale_surface(screen.copy())

            if not music_switched and elapsed > 1000:
                try:
                    pygame.mixer.music.load(resource_path('soundtrack/gameover.mp3'))
                    pygame.mixer.music.play(-1, 30.0, 1000)  # loops=-1, start=30.0, fade_ms=1000
                    pygame.mixer.music.set_volume(0.7)
                    music_switched = True
                except pygame.error:
                    print('Unable to load gameover music.')
            if gray_screen is not None and elapsed < 2000:
                screen.blit(gray_screen, (0, 0))
            elif gray_screen is not None and elapsed < 5000:
                screen.blit(gray_screen, (0, 0))
                fade_alpha = int((elapsed - 2000) / 3000 * 255)
                fade_surface = pygame.Surface((screen_rect.width, screen_rect.height))
                fade_surface.set_alpha(fade_alpha)
                fade_surface.fill((0, 0, 0))
                screen.blit(fade_surface, (0, 0))
            elif gray_screen is not None:
                draw_cinematic_end(screen, score, mouse_pos, gameover_bg)
        elif current_state == GAME_OVER:
            return_button_rect = draw_game_over(screen, mouse_pos, score, gameover_bg)

        update_targeting_reticle(mouse_pos, virus_group if current_state == PLAYING else None)

        window_w, window_h = display_screen.get_size()
        scale = min(window_w / VIRTUAL_RES[0], window_h / VIRTUAL_RES[1])
        new_size = (int(VIRTUAL_RES[0] * scale), int(VIRTUAL_RES[1] * scale))
        scaled_surface = pygame.transform.smoothscale(internal_surface, new_size)
        offset = ((window_w - new_size[0]) // 2, (window_h - new_size[1]) // 2)

        global global_offset, global_scale
        global_offset = offset
        global_scale = scale

        display_screen.fill((0, 0, 0))
        display_screen.blit(scaled_surface, offset)
        pygame.display.flip()
        if current_state == CINEMATIC_DEATH and current_time - cinematic_start < 2000:
            clock.tick(30)
        else:
            clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
