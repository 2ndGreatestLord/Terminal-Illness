"""
Modifier system for applying card upgrades to the player.
Each modifier stacks and applies to future antibodies/player stats.
"""

import random


def reset_player_stats_to_base(player):
    """
    Reset player stats to base values for recalculation.
    Preserves active health clamped to new max_health.
    """
    if hasattr(player, 'base_speed'):
        player.speed = player.base_speed

    if hasattr(player, 'base_max_health'):
        player.max_health = player.base_max_health
        player.health = min(player.health, player.max_health)

    if hasattr(player, 'base_size'):
        old_center = player.rect.center
        player.size = player.base_size
        player._update_image_with_size(player.size)
        player.rect.center = old_center

    # Reset antibody modifiers
    player.cooldown_multiplier = 1.0
    player.antibody_size_multiplier = 1.0
    player.antibody_damage_multiplier = 1.0
    player.antibody_speed_multiplier = 1.0
    player.antibody_pierce_count = 0
    player.scattershot_enabled = False
    player.organ_max_health_bonus = 0
    player.refill_organ_on_upgrade = False


def recalculate_modifiers(player):
    """
    Recalculate all modifiers based on player.active_cards.
    This ensures proper stacking and consistency.

    Call this after adding a new card to player.active_cards.
    """
    # Reset to base stats first
    reset_player_stats_to_base(player)

    # Clear modifiers list and re-apply each card
    player.modifiers = []
    for card_type in player.active_cards:
        apply_card_modifier(player, card_type)


def apply_card_modifier(player, card_type):
    """
    Apply a card modifier to the player.
    Modifiers are stored in player.modifiers list and applied to future antibodies.

    Args:
        player: Player instance
        card_type: String identifier (e.g. "rapid_fire", "pierce", "well_nourished")
    """

    # Initialize modifiers list if not present
    if not hasattr(player, 'modifiers'):
        player.modifiers = []

    powerup = POWERUP_DEFS.get(card_type)
    if powerup is None:
        return

    apply_fn = powerup.get("apply_fn")
    if callable(apply_fn):
        apply_fn(player)


def apply_rapid_fire_modifier(player):
    """
    Rapid Fire upgrade:
    - Decreases fire_delay (cooldown) by 25% using cooldown_multiplier
    - Reduces antibody size by 10%
    - Reduces antibody damage by 10%
    """
    # Add to modifiers list for tracking
    player.modifiers.append("rapid_fire")

    # Decrease cooldown by 25% (multiply by 0.75)
    if not hasattr(player, 'cooldown_multiplier'):
        player.cooldown_multiplier = 1.0
    player.cooldown_multiplier *= 0.75

    # Store antibody size/damage multipliers
    if not hasattr(player, 'antibody_size_multiplier'):
        player.antibody_size_multiplier = 1.0
    if not hasattr(player, 'antibody_damage_multiplier'):
        player.antibody_damage_multiplier = 1.0

    player.antibody_size_multiplier *= 0.9
    player.antibody_damage_multiplier *= 0.9


def apply_pierce_modifier(player):
    """
    Pierce upgrade:
    - Increases antibody pierce_count by 1
    - Allows antibodies to pass through enemies
    """
    # Add to modifiers list
    player.modifiers.append("pierce")

    # Track pierce count
    if not hasattr(player, 'antibody_pierce_count'):
        player.antibody_pierce_count = 0

    player.antibody_pierce_count += 1


def apply_well_nourished_modifier(player):
    """
    Well Nourished upgrade:
    - Increases player size by 25%
    - Increases max_health by 50%
    - Fully heals player
    """
    # Add to modifiers list
    player.modifiers.append("well_nourished")

    # Increase player size by 25% (and rect/mask with it)
    old_center = player.rect.center
    player.size = getattr(player, 'size', 1.0)
    player.size *= 1.25

    # Regenerate image at new size
    player._update_image_with_size(player.size)
    player.rect.center = old_center

    # Increase max health by 50%
    if not hasattr(player, 'max_health'):
        player.max_health = 100  # Default max health

    player.max_health = int(player.max_health * 1.5)
    # Fully heal player when selecting Well Nourished
    player.health = player.max_health


def apply_scattershot_modifier(player):
    """Scattershot upgrade:
    - Fires 3 antibodies per shot (handled in projectile firing path)
    - Reduces damage per antibody
    - Unique: can only be acquired once per run
    """
    player.modifiers.append("scattershot")
    player.scattershot_enabled = True

    if not hasattr(player, 'antibody_damage_multiplier'):
        player.antibody_damage_multiplier = 1.0
    player.antibody_damage_multiplier *= 0.7


def apply_increased_organ_health_modifier(player):
    """Increased Organ Health upgrade:
    - Increase organ max health cap by +50 (stacks)
    - Fully refill organ health when acquired
    """
    player.modifiers.append("increased_organ_health")

    if not hasattr(player, 'organ_max_health_bonus'):
        player.organ_max_health_bonus = 0
    player.organ_max_health_bonus += 50
    player.refill_organ_on_upgrade = True


def apply_big_shot_modifier(player):
    """Big Shot upgrade (stacking):
    - Increases antibody damage
    - Increases antibody size
    - Slows fire rate
    - Slows antibody travel speed
    """
    player.modifiers.append("big_shot")

    if not hasattr(player, 'cooldown_multiplier'):
        player.cooldown_multiplier = 1.0
    if not hasattr(player, 'antibody_size_multiplier'):
        player.antibody_size_multiplier = 1.0
    if not hasattr(player, 'antibody_damage_multiplier'):
        player.antibody_damage_multiplier = 1.0
    if not hasattr(player, 'antibody_speed_multiplier'):
        player.antibody_speed_multiplier = 1.0

    player.cooldown_multiplier *= 1.2
    player.antibody_size_multiplier *= 1.25
    player.antibody_damage_multiplier *= 1.35
    player.antibody_speed_multiplier *= 0.8


def apply_sniper_modifier(player):
    """Sniper upgrade (stacking, capped):
    - Increases antibody travel speed by +25% per stack
    - Max 4 stacks (200% speed)
    """
    player.modifiers.append("sniper")

    if not hasattr(player, 'antibody_speed_multiplier'):
        player.antibody_speed_multiplier = 1.0
    player.antibody_speed_multiplier *= 1.25


def register_powerup(
    powerup_id,
    display_name,
    color,
    description,
    apply_fn,
    unique=False,
    max_stacks=None,
    weight=1.0,
):
    """Register a level-up powerup option.

    This is the single entry point for adding future powerups.
    """
    POWERUP_DEFS[powerup_id] = {
        "id": powerup_id,
        "display_name": display_name,
        "color": color,
        "description": description,
        "apply_fn": apply_fn,
        "unique": unique,
        "max_stacks": max_stacks,
        "weight": float(weight),
    }


def get_powerup_def(powerup_id):
    return POWERUP_DEFS.get(powerup_id)


def get_all_powerup_defs():
    return list(POWERUP_DEFS.values())


def can_acquire_powerup(player, powerup_id):
    powerup = POWERUP_DEFS.get(powerup_id)
    if powerup is None:
        return False

    active_cards = getattr(player, "active_cards", [])

    if powerup.get("unique", False) and powerup_id in active_cards:
        return False

    max_stacks = powerup.get("max_stacks")
    if max_stacks is not None:
        current_stacks = sum(1 for card_id in active_cards if card_id == powerup_id)
        if current_stacks >= max_stacks:
            return False

    return True


def roll_level_up_powerups(player, count=3):
    """Return up to `count` unique choices for the level-up menu.

    Unique powerups are removed from the candidate pool once acquired.
    Non-unique powerups can be offered again in later level-ups.
    """
    candidates = [
        p for p in POWERUP_DEFS.values()
        if can_acquire_powerup(player, p["id"])
    ]

    if not candidates:
        return []

    rolled = []
    pool = candidates.copy()
    draws = min(count, len(pool))

    for _ in range(draws):
        total_weight = sum(max(0.0, p.get("weight", 1.0)) for p in pool)

        if total_weight <= 0.0:
            choice = random.choice(pool)
        else:
            pick = random.uniform(0.0, total_weight)
            running = 0.0
            choice = pool[-1]
            for powerup in pool:
                running += max(0.0, powerup.get("weight", 1.0))
                if pick <= running:
                    choice = powerup
                    break

        rolled.append(choice)
        pool.remove(choice)

    return rolled


POWERUP_DEFS = {}

# Existing default powerups
register_powerup(
    powerup_id="rapid_fire",
    display_name="Rapid Fire",
    color=(255, 100, 0),
    description="Accelerated Discharge",
    apply_fn=apply_rapid_fire_modifier,
    unique=False,
    weight=1.0,
)

register_powerup(
    powerup_id="pierce",
    display_name="Pierce",
    color=(100, 200, 255),
    description="Enhanced Penetration",
    apply_fn=apply_pierce_modifier,
    unique=False,
    weight=1.0,
)

register_powerup(
    powerup_id="well_nourished",
    display_name="Well Nourished",
    color=(255, 0, 100),
    description="Cellular Fortification",
    apply_fn=apply_well_nourished_modifier,
    unique=False,
    weight=1.0,
)

register_powerup(
    powerup_id="scattershot",
    display_name="Scattershot",
    color=(120, 255, 120),
    description="3 Antibodies, Lower Per-Shot Damage",
    apply_fn=apply_scattershot_modifier,
    unique=True,
    weight=0.9,
)

register_powerup(
    powerup_id="increased_organ_health",
    display_name="Increased Organ Health",
    color=(255, 80, 80),
    description="+50 Organ Max HP, Refill Organ",
    apply_fn=apply_increased_organ_health_modifier,
    unique=False,
    weight=0.95,
)

register_powerup(
    powerup_id="big_shot",
    display_name="Big Shot",
    color=(255, 170, 60),
    description="Bigger, Stronger, Slower Antibodies",
    apply_fn=apply_big_shot_modifier,
    unique=False,
    weight=0.95,
)

register_powerup(
    powerup_id="sniper",
    display_name="Sniper",
    color=(120, 220, 255),
    description="+25% Antibody Speed (Max 200%)",
    apply_fn=apply_sniper_modifier,
    unique=False,
    max_stacks=4,
    weight=0.9,
)
