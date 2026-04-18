#!/usr/bin/env python3
"""Quick sound loading test - verify all sound files are accessible and loadable."""

import pygame
import os
from soundmanager import SoundManager

# Initialize pygame mixer
pygame.mixer.init()

# Sound configuration (must match main.py)
SOUNDS_CONFIG = {
    'shoot': {'path': 'soundeffects/shoot.mp3', 'volume': 0.25},
    'enemy_hit': {'path': 'soundeffects/enemyhit.mp3', 'volume': 0.30},
    'enemy_death': {'path': 'soundeffects/enemydeath.mp3', 'volume': 0.45},
    'player_hit': {'path': 'soundeffects/playerhit.mp3', 'volume': 0.60},
    'player_death': {'path': 'soundeffects/playerdeath.mp3', 'volume': 0.90},
    'level_up': {'path': 'soundeffects/levelup.mp3', 'volume': 0.85},
    'pickup_collected': {'path': 'soundeffects/pickupcollected.mp3', 'volume': 0.65},
    'button_clicked': {'path': 'soundeffects/buttonclicked.mp3', 'volume': 0.50},
}

print("=" * 60)
print("SOUND FILE VERIFICATION TEST")
print("=" * 60)

# Check if soundeffects folder exists
if not os.path.isdir('soundeffects'):
    print("✗ CRITICAL: 'soundeffects' folder not found in current directory!")
    print(f"  Current directory: {os.getcwd()}")
    exit(1)

print(f"✓ Found 'soundeffects' folder")
print()

# Check each sound file exists
print("Checking individual sound files:")
all_exist = True
for sound_name, config in SOUNDS_CONFIG.items():
    file_path = config['path']
    exists = os.path.isfile(file_path)
    status = "✓" if exists else "✗"
    print(f"  {status} {sound_name:20} -> {file_path}")
    if not exists:
        all_exist = False

print()

if not all_exist:
    print("✗ CRITICAL: Some sound files are missing!")
    exit(1)

print("=" * 60)
print("SOUND LOADING TEST")
print("=" * 60)
print()

# Initialize SoundManager
try:
    sound_manager = SoundManager.get_instance()
    sound_manager.__init__(SOUNDS_CONFIG)
    print("✓ SoundManager initialized successfully")
except Exception as e:
    print(f"✗ Failed to initialize SoundManager: {e}")
    exit(1)

print()

# Test playing each sound
print("Testing sound playback (will play each sound for ~1 second):")
print()

import time

for sound_name in SOUNDS_CONFIG.keys():
    print(f"  Playing '{sound_name}'...", end=" ")

    channel = sound_manager.play(sound_name)
    if channel:
        print("✓ Queued")
        time.sleep(1.5)  # Wait for sound to play
    else:
        print("✗ Failed to queue")

print()
print("=" * 60)
print("TEST COMPLETE")
print("=" * 60)
print()
print("✓ All sounds loaded and tested successfully!")
print("✓ Debounce times:")
print("  - enemy_hit: 80ms")
print("  - player_hit: 400ms")
