#!/usr/bin/env python3
"""Diagnostic test for shoot sound timing."""

import pygame
from projectiles import Antibody
from soundmanager import SoundManager

# Initialize pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))

# Initialize sound manager
sound_manager = SoundManager.get_instance()
SOUNDS_CONFIG = {
    'shoot': {'path': 'soundeffects/shoot.mp3', 'volume': 0.15},
}
sound_manager.__init__(SOUNDS_CONFIG)

print("=" * 60)
print("SHOOT SOUND TIMING TEST")
print("=" * 60)
print()

# Create a mock player object
class MockPlayer:
    def __init__(self):
        self.rect = pygame.Rect(0, 0, 20, 20)
        self.rect.center = (400, 300)
        self.aim_angle = 0
        self.fire_rate_multiplier = 1.0
        self.cooldown_multiplier = 1.0
        self.antibody_size_multiplier = 1.0
        self.antibody_damage_multiplier = 1.0
        self.antibody_pierce_count = 0

player = MockPlayer()
screen_rect = screen.get_rect()

print("Test 1: Fire a bullet and check if sound plays")
print("-" * 60)

# Fire a bullet
bullet = Antibody.fire_from_player(player, screen_rect, None)

if bullet:
    print("✓ Bullet created successfully")
    print(f"  Position: {bullet.rect.center}")
    print(f"  Velocity: {bullet.velocity}")
    print()
    print("Check your audio output for 'shoot' sound")
    print("(The sound should have played immediately, not after trajectory)")
else:
    print("✗ Failed to create bullet")

print()
print("=" * 60)
print("TEST COMPLETE")
print("=" * 60)

pygame.quit()
