import pygame
import math
import os
from resource_utils import resource_path


# Fonts will be initialized after pygame.init() is called
FONT_NORMAL = None
FONT_TITLE = None
FONT_SMALL = None
_font_cache = {}

def get_font(size, bold=False):
    """Get a font of the specified size, using the custom font.otf if possible."""
    key = (size, bold)
    if key not in _font_cache:
        try:
            font = pygame.font.Font(resource_path('sprites/font.otf'), int(size))
            if bold:
                try: font.set_bold(True)
                except: pass
            _font_cache[key] = font
        except:
            _font_cache[key] = pygame.font.Font(resource_path('sprites/font.otf'), int(size))
    return _font_cache[key]

class Button(pygame.sprite.Sprite):
    _base_texture = None
    _hover_texture = None

    def __init__(self, text, x, y, width=340, height=64):
        super().__init__()
        self.text = text
        self.rect = pygame.Rect(x, y, width, height)

        # Load the base and hover/active textures exactly once
        if Button._base_texture is None:
            try:
                Button._base_texture = pygame.image.load(resource_path('sprites/btn_base.png')).convert_alpha()
            except:
                Button._base_texture = pygame.Surface((width, height), pygame.SRCALPHA)
                pygame.draw.rect(Button._base_texture, (100, 100, 100), Button._base_texture.get_rect())
                pygame.draw.rect(Button._base_texture, (200, 200, 200), Button._base_texture.get_rect(), 2)

        if Button._hover_texture is None:
            try:
                Button._hover_texture = pygame.image.load(resource_path('sprites/btn_active.png')).convert_alpha()
            except:
                Button._hover_texture = pygame.Surface((width, height), pygame.SRCALPHA)
                pygame.draw.rect(Button._hover_texture, (150, 150, 150), Button._hover_texture.get_rect())
                pygame.draw.rect(Button._hover_texture, (200, 200, 200), Button._hover_texture.get_rect(), 2)

        self.btn_base = pygame.transform.smoothscale(Button._base_texture, (width, height))
        self.btn_hover = pygame.transform.smoothscale(Button._hover_texture, (width, height))

        self.image = self.btn_base

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        hover = self.rect.collidepoint(mouse_pos)

        if hover:
            self.image = self.btn_hover
            text_color = (139, 0, 139)  # Dark Magenta / Deep Violet
        else:
            self.image = self.btn_base
            text_color = (255, 255, 255)  # White

        surface.blit(self.image, self.rect)

        font = get_font(36)
        text_surf = font.render(self.text, True, text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

def init_fonts():
    """Initialize fonts after pygame.init() is called."""
    global FONT_NORMAL, FONT_TITLE, FONT_SMALL
    FONT_NORMAL = get_font(32)
    FONT_TITLE = get_font(48)
    FONT_SMALL = get_font(20)


def draw_text_with_glow(surface, text, font, x, y, shadow_color=(0, 255, 255), text_color=(255, 255, 255)):
    """Draw text with a glow effect: shadow at offset in cyan, then white text."""
    shadow_text = font.render(text, True, shadow_color)
    surface.blit(shadow_text, (x + 1, y + 1))
    main_text = font.render(text, True, text_color)
    surface.blit(main_text, (x, y))

class GameInfoState:
    _bg_image = None
    _sprites_loaded = False

    def __init__(self, mode, screen_rect):
        self.mode = mode
        if GameInfoState._bg_image is None:
            try:
                GameInfoState._bg_image = pygame.image.load(resource_path('sprites/howtoplaydirectory.png')).convert_alpha()
            except pygame.error:
                GameInfoState._bg_image = pygame.Surface(screen_rect.size)
                GameInfoState._bg_image.fill((20, 20, 20))

        self.bg = pygame.transform.smoothscale(GameInfoState._bg_image, screen_rect.size)

        self.back_button = Button("BACK", 0, 0, 340, 64)

        # Calculate horizontal center for the empty "screen" area of the background graphic
        panel_center_x = screen_rect.centerx + int(screen_rect.width * 0.13)
        self.back_button.rect.center = (panel_center_x, screen_rect.centery + 195)

        if not GameInfoState._sprites_loaded:
            def load_sprite(path, size=64):
                try:
                    img = pygame.image.load(resource_path(path)).convert_alpha()
                    return pygame.transform.smoothscale(img, (size, size))
                except pygame.error:
                    surf = pygame.Surface((size, size), pygame.SRCALPHA)
                    pygame.draw.circle(surf, (255, 255, 255), (size//2, size//2), size//2)
                    return surf

            GameInfoState.wbc_sprite = load_sprite('sprites/player.png', 64)
            GameInfoState.virus_sprite = load_sprite('sprites/virus.png', 64)
            GameInfoState.stalker_sprite = load_sprite('sprites/stalker.png', 64)
            GameInfoState.tank_sprite = load_sprite('sprites/tank.png', 64)
            GameInfoState.boss_sprite = load_sprite('sprites/boss.png', 80)
            GameInfoState._sprites_loaded = True

    def draw(self, screen, mouse_pos):
        screen.blit(self.bg, (0, 0))
        screen_rect = screen.get_rect()
        center_x = screen_rect.centerx
        center_y = screen_rect.centery

        if self.mode == 'HOW_TO_PLAY':
            panel_center_x = center_x + int(screen_rect.width * 0.12)
            title = "SYSTEM PROTOCOLS"
            draw_text_with_glow(screen, title, FONT_TITLE, panel_center_x - FONT_TITLE.size(title)[0]//2, center_y - 200)

            instructions = [
                "WASD/ARROWS - CELLULAR NAVIGATION",
                "SPACE - ANTIBODY DISCHARGE",
                "OBJECTIVE - PATHOGENIC CONTAINMENT",
                "WARNING - MUTATION DETECTED WAVE 10"
            ]
            line_start_y = center_y - 80
            for i, text in enumerate(instructions):
                text_width = FONT_NORMAL.size(text)[0]
                x_pos = panel_center_x - text_width // 2
                draw_text_with_glow(screen, text, FONT_NORMAL, x_pos, line_start_y + i * 50)

        elif self.mode == 'DIRECTORY':
            panel_center_x = center_x + int(screen_rect.width * 0.08)
            title = "PATHOGEN ARCHIVE"
            draw_text_with_glow(screen, title, FONT_TITLE, panel_center_x - FONT_TITLE.size(title)[0]//2, center_y - 235)

            entries = [
                (GameInfoState.wbc_sprite, "WBC (Player): Defensive cell. Neutralizes pathogens. (Cyan Core)"),
                (GameInfoState.virus_sprite, "Virus: Standard pathogen. Targets the organ. (Green Body)"),
                (GameInfoState.stalker_sprite, "Stalker: Agile hunter. Targeted organ attacks. (Amber Core)"),
                (GameInfoState.tank_sprite, "Tank: Armored host. Massive systemic impact. (Violet Shell)"),
                (GameInfoState.boss_sprite, "Pathogen Prime (Boss): Alpha threat. Spawns invasive mutations. (Neon Green)")
            ]

            line_start_y = center_y - 120
            # Calculate total width to center everything nicely
            for i, (sprite, text) in enumerate(entries):
                y_pos = line_start_y + i * 65
                sprite_rect = sprite.get_rect(center=(panel_center_x - 360, y_pos))
                screen.blit(sprite, sprite_rect)

                # We align text tightly near the sprite
                draw_text_with_glow(screen, text, FONT_SMALL, panel_center_x - 290, y_pos - FONT_SMALL.size(text)[1]//2)

        self.back_button.draw(screen)
        return self.back_button.rect
class Card(pygame.sprite.Sprite):
    """Sprite-based upgrade card with flipping entrance animation and focus zoom."""

    def __init__(self, powerup_id, type_name, color, description, x, y, width=120, height=150, start_delay_ms=0, sprite_image=None):
        super().__init__()
        self.powerup_id = powerup_id
        self.type_name = type_name
        self.color = color
        self.description = description
        self.width = width
        self.height = height
        self.sprite_image = sprite_image
        self.base_x = x
        self.base_y = y
        self.x = x
        self.y = y

        # Entrance animation
        self.entrance_start_time = start_delay_ms  # When this card starts animating
        self.entrance_duration = 500  # Flipping animation duration (0.5 seconds)
        self.current_flip = 0  # Current flip angle (0-90 degrees)

        # Focus management
        self.is_focused = False
        self.focus_scale = 1.0  # Current scale (lerp toward 1.5 when focused)
        self.focus_transition_duration = 100  # ms to transition to/from focused
        self.focus_transition_time = 0  # Current time in transition

        # Base image (flat, unrotated)
        self._create_base_image()
        self.image = self.base_image.copy()
        self.rect = self.image.get_rect(center=(x, y))

    @staticmethod
    def _fit_font_to_width(text, max_width, start_size=28, min_size=14):
        size = start_size
        while size > min_size:
            font = get_font(size)
            if font.size(text)[0] <= max_width:
                return font
            size -= 1
        return get_font(min_size)

    def _create_base_image(self):
        """Create the base card image (unrotated)."""
        self.base_image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        # Card background (sprite if available, fallback to color card)
        if self.sprite_image is not None:
            self.base_image.blit(self.sprite_image, (0, 0))
        else:
            pygame.draw.rect(self.base_image, self.color, (0, 0, self.width, self.height))
        pygame.draw.rect(self.base_image, (255, 255, 255), (0, 0, self.width, self.height), 3)

    def _draw_glow_text(self, surface, text, font, center, main_color=(220, 255, 255), glow_color=(255, 0, 255)):
        glow = font.render(text, True, glow_color)
        glow_rect = glow.get_rect(center=(center[0] + 2, center[1] + 2))
        surface.blit(glow, glow_rect)

        main = font.render(text, True, main_color)
        main_rect = main.get_rect(center=center)
        surface.blit(main, main_rect)

    def update_entrance(self, current_ms):
        """Update entrance animation with sine-wave flip from 90 to 0 degrees."""
        time_since_start = current_ms - self.entrance_start_time

        if time_since_start < 0:
            # Card hasn't started animating yet
            self.current_flip = 90
        elif time_since_start >= self.entrance_duration:
            # Animation complete
            self.current_flip = 0
        else:
            # Sine-wave interpolation: starts at 90, ends at 0
            progress = time_since_start / self.entrance_duration
            # Sine wave goes from 1 to 0 over progress 0 to 1
            self.current_flip = 90 * math.sin((1 - progress) * math.pi / 2)

    def update_focus(self, is_focused):
        """Smoothly transition focus scale using linear interpolation."""
        target_scale = 1.5 if is_focused else 1.0

        if is_focused != self.is_focused:
            # Focus state changed, start transition
            self.is_focused = is_focused
            self.focus_transition_time = 0

        # Lerp toward target scale
        if self.focus_transition_time < self.focus_transition_duration:
            progress = self.focus_transition_time / self.focus_transition_duration
            self.focus_scale = 1.0 + (target_scale - 1.0) * progress
            self.focus_transition_time += 16  # Approximate 60 FPS
        else:
            self.focus_scale = target_scale

    def get_rect(self):
        """Return collision rect for click detection, centered at card position."""
        rect = pygame.Rect(0, 0, self.width, self.height)
        rect.center = (int(self.x), int(self.y))
        return rect

    def draw(self, surface):
        """Draw the card with flip animation and optional focus zoom."""
        # Apply flip effect: reduce width based on flip angle
        flip_scale = math.cos(math.radians(self.current_flip))

        if flip_scale <= 0.01:
            # Card is fully flipped (edge-on), don't draw
            return

        # Create flipped image by scaling width
        flipped_width = max(1, int(self.width * flip_scale))
        flipped_image = pygame.transform.scale(self.base_image, (flipped_width, self.height))

        # Apply focus zoom
        if self.is_focused or self.focus_scale > 1.01:
            scaled_width = int(flipped_width * self.focus_scale)
            scaled_height = int(self.height * self.focus_scale)
            flipped_image = pygame.transform.scale(flipped_image, (scaled_width, scaled_height))

            # Draw drop shadow
            shadow_offset_x = 3
            shadow_offset_y = 3
            shadow_surface = pygame.Surface((scaled_width, scaled_height), pygame.SRCALPHA)
            shadow_surface.fill((0, 0, 0, 100))
            shadow_rect = shadow_surface.get_rect(center=(self.x + shadow_offset_x, self.y + shadow_offset_y + 20))
            surface.blit(shadow_surface, shadow_rect)
        else:
            scaled_width = flipped_width
            scaled_height = self.height

        # Draw card centered at position
        card_rect = flipped_image.get_rect(center=(self.x, self.y))
        surface.blit(flipped_image, card_rect)

        # Draw centered card text overlay with glow once card is mostly face-on.
        if flip_scale > 0.6:
            title_font = self._fit_font_to_width(self.type_name, int(scaled_width * 0.9), start_size=26, min_size=12)
            desc_font = self._fit_font_to_width(self.description, int(scaled_width * 0.9), start_size=18, min_size=10)

            self._draw_glow_text(
                surface,
                self.type_name,
                title_font,
                (self.x, int(self.y - scaled_height * 0.22)),
                main_color=(220, 255, 255),
                glow_color=(255, 0, 255),
            )
            self._draw_glow_text(
                surface,
                self.description,
                desc_font,
                (self.x, int(self.y + scaled_height * 0.06)),
                main_color=(245, 245, 245),
                glow_color=(255, 0, 255),
            )


class CardSelectionMenu:
    """Menu for selecting upgrade cards with entrance and hover animations."""

    _bg_image = None

    def __init__(self, screen, player, powerup_choices=None):
        self.screen = screen
        self.player = player
        self.screen_rect = screen.get_rect()
        self.menu_open_time = pygame.time.get_ticks()  # Track when menu opened

        if CardSelectionMenu._bg_image is None:
            try:
                CardSelectionMenu._bg_image = pygame.image.load(resource_path('sprites/levelup.png')).convert_alpha()
            except pygame.error:
                CardSelectionMenu._bg_image = pygame.Surface(self.screen_rect.size)
                CardSelectionMenu._bg_image.fill((0, 0, 0))

        self.bg = pygame.transform.smoothscale(CardSelectionMenu._bg_image, self.screen_rect.size)

        if powerup_choices is None:
            from modifiers import get_all_powerup_defs
            powerup_choices = get_all_powerup_defs()[:3]

        # Card slots mapped from a 1024x576 reference layout.
        ref_w, ref_h = 1024, 576
        sx = self.screen_rect.width / ref_w
        sy = self.screen_rect.height / ref_h
        ui_scale = min(sx, sy)

        card_width = int(150 * ui_scale)
        card_height = int(228 * ui_scale)

        slot_centers = [
            (int(290 * sx), int(310 * sy)),
            (int(512 * sx), int(310 * sy)),
            (int(734 * sx), int(310 * sy)),
        ]

        self.cards = []
        for i, powerup in enumerate(powerup_choices):
            slot_x, slot_y = slot_centers[min(i, len(slot_centers) - 1)]
            self.cards.append(
                Card(
                    powerup_id=powerup["id"],
                    type_name=powerup["display_name"],
                    color=powerup.get("color", (120, 120, 120)),
                    description=powerup.get("description", ""),
                    x=slot_x,
                    y=slot_y,
                    width=card_width,
                    height=card_height,
                    start_delay_ms=i * 100,
                    sprite_image=None,
                )
            )

        self.clicked_card = None
        self.focused_card = None

    def update(self, elapsed_ms):
        """Update entrance animations, focus state, and hover effects."""
        current_ms = pygame.time.get_ticks() - self.menu_open_time
        mouse_pos = pygame.mouse.get_pos()

        # Update entrance animation for all cards
        for card in self.cards:
            card.update_entrance(current_ms)

        # Focus management: only one card can be focused at a time
        new_focused_card = None
        for card in self.cards:
            card_rect = card.get_rect()
            if card_rect.collidepoint(mouse_pos):
                new_focused_card = card
                break

        # Update focus for all cards
        for card in self.cards:
            is_focused = (card == new_focused_card)
            card.update_focus(is_focused)

        self.focused_card = new_focused_card

    def draw(self):
        """Draw the level-up background and cards."""
        self.screen.blit(self.bg, (0, 0))

        # Draw title and subtitle
        center_x = self.screen_rect.centerx

        font_title = get_font(66)
        title = font_title.render(f"LEVEL UP! (Level {self.player.level})", True, (0, 255, 0))
        title_rect = title.get_rect(center=(center_x, int(self.screen_rect.height * 0.11)))
        self.screen.blit(title, title_rect)

        font_subtitle = get_font(26)
        subtitle = font_subtitle.render("Click a card to select:", True, (200, 200, 200))
        subtitle_rect = subtitle.get_rect(center=(center_x, int(self.screen_rect.height * 0.19)))
        self.screen.blit(subtitle, subtitle_rect)

        # Draw cards
        for card in self.cards:
            card.draw(self.screen)

    def handle_click(self, mouse_pos):
        """Check if a card was clicked and return its powerup_id."""
        for card in self.cards:
            rect = card.get_rect()
            if rect.collidepoint(mouse_pos):
                self.clicked_card = card.powerup_id
                return card.powerup_id
        return None


def draw_xp_bar(screen, player):
    if not player:
        return

    bar_width = 460
    bar_height = 36
    bar_x = (screen.get_width() - bar_width) // 2
    bar_y = screen.get_height() - bar_height - 10

    pygame.draw.rect(screen, (255, 0, 0), (bar_x, bar_y, bar_width, bar_height))

    xp_width = int(bar_width * (player.current_xp / max(1, player.xp_to_next_level)))
    pygame.draw.rect(screen, (0, 255, 255), (bar_x, bar_y, xp_width, bar_height))

    font = get_font(20, bold=False)
    level_text = font.render(f"GEN {player.level}", True, (0, 0, 0))
    xp_text = font.render(f"XP: {player.current_xp}/{player.xp_to_next_level}", True, (0, 0, 0))

    level_rect = level_text.get_rect(midleft=(bar_x + 10, bar_y + bar_height // 2))
    xp_rect = xp_text.get_rect(midright=(bar_x + bar_width - 10, bar_y + bar_height // 2))

    screen.blit(level_text, level_rect)
    screen.blit(xp_text, xp_rect)

def draw_game_over(screen, mouse_pos, score, gameover_bg=None):
    if gameover_bg:
        screen.blit(gameover_bg, (0, 0))
    else:
        screen.fill((0, 0, 0))

    screen_rect = screen.get_rect()
    center_x = screen_rect.centerx
    center_y = screen_rect.centery

    # Score
    font_score = get_font(36)
    score_text = font_score.render(f"Final Score: {score}", True, (255, 255, 255))
    score_rect = score_text.get_rect(center=(center_x, center_y + 100))
    screen.blit(score_text, score_rect)

    # Return button
    temp_button = Button("RETURN TO MAIN MENU", 0, 0, 500, 64)
    temp_button.rect.center = (center_x, center_y + 180)
    temp_button.draw(screen)

    return temp_button.rect
