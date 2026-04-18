import pygame
import time
from typing import Dict, Optional


class SoundManager(object):
    """
    Singleton SoundManager - manages all sound effects for the game using pygame.mixer.

    Features:
    - Pre-loads all sounds into memory to prevent disk-reading lag
    - Supports per-sound volume scaling
    - Plays sounds on available mixer channels
    - Implements per-sound debouncing to prevent audio clipping

    Access via: SoundManager.get_instance()
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SoundManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls):
        """Get or create the SoundManager singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, sounds_config: Dict[str, Dict] = None, num_channels: int = 8):
        """
        Initialize the SoundManager (Singleton - only runs once).

        Args:
            sounds_config: Dictionary mapping sound names to their config.
                          Example: {
                              'shoot': {'path': 'soundeffects/shoot.mp3', 'volume': 0.25},
                              'enemy_hit': {'path': 'soundeffects/enemyhit.mp3', 'volume': 0.30},
                              ...
                          }
            num_channels: Number of mixer channels to allocate (default 8)
        """
        # If already initialized and no config provided, skip
        if self._initialized and sounds_config is None:
            return

        # If config provided, allow re-initialization
        if sounds_config and self._initialized:
            self.sounds.clear()
            self.volume_levels.clear()
            self.last_played_time.clear()

        pygame.mixer.init()
        pygame.mixer.set_num_channels(num_channels)

        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.volume_levels: Dict[str, float] = {}
        self.last_played_time: Dict[str, float] = {}

        # Dedicated channel for high-priority UI sounds (levelup, wave_clear)
        # Channel 7 (0-indexed) is reserved exclusively for UI sounds to ensure they always play
        self.ui_channel = pygame.mixer.Channel(7)
        self.ui_channel.set_volume(1.0)  # Always max volume for UI feedback

        # Dedicated channel for player taking damage/dying (channel 6)
        self.player_channel = pygame.mixer.Channel(6)
        self.player_channel.set_volume(1.0)

        # Per-sound debounce times (in seconds)
        self.debounce_times: Dict[str, float] = {
            'enemy_hit': 0.080,      # 80ms debounce for enemy_hit
            'player_hit': 0.400,     # 400ms debounce for player_hit
        }

        # Pre-load all sounds if config provided
        if sounds_config:
            for sound_name, config in sounds_config.items():
                self._load_sound(sound_name, config['path'], config.get('volume', 1.0))

        self._initialized = True

    def _load_sound(self, sound_name: str, file_path: str, volume: float = 1.0) -> None:
        """
        Load a single sound file into memory.

        Args:
            sound_name: Name key for the sound (e.g., 'shoot', 'hit')
            file_path: Path to the sound file
            volume: Volume level (0.0 to 1.0)
        """
        try:
            sound = pygame.mixer.Sound(file_path)
            self.sounds[sound_name] = sound
            self.volume_levels[sound_name] = max(0.0, min(1.0, volume))  # Clamp 0-1
            self.last_played_time[sound_name] = 0.0
            print(f"✓ Loaded sound: {sound_name} (volume: {self.volume_levels[sound_name]:.1%})")
        except Exception as e:
            print(f"✗ Failed to load sound '{sound_name}' from {file_path}: {e}")

    def play(self, sound_name: str) -> Optional[pygame.mixer.Channel]:
        """
        Play a sound effect on an available channel.

        Special handling:
        - 'levelup' and 'wave_clear' use the dedicated UI channel (channel 7) at max volume
        - Other sounds are debounced (enemy_hit: 80ms, player_hit: 400ms)
        - Checks if sound exists before attempting to play
        - Sets volume according to per-sound configuration

        Args:
            sound_name: Name of the sound to play (e.g., 'shoot', 'enemy_hit', 'levelup')

        Returns:
            pygame.mixer.Channel if sound was played, None otherwise
        """
        if sound_name not in self.sounds:
            print(f"⚠ Sound not found: {sound_name}")
            return None

        # High-priority UI sounds use the dedicated UI channel with guaranteed playback
        if sound_name in ['level_up', 'wave_clear']:
            try:
                sound = self.sounds[sound_name]
                # Force maximum volume for UI sounds to override combat noise
                self.ui_channel.set_volume(1.0)
                print(f"♪ Playing UI sound '{sound_name}' on DEDICATED UI channel: {self.ui_channel}, volume=1.00 (GUARANTEED)")
                self.ui_channel.play(sound)
                print(f"✓ UI Channel.play() called, ui_channel is now busy: {self.ui_channel.get_busy()}")
                return self.ui_channel
            except Exception as e:
                print(f"✗ Error playing UI sound '{sound_name}': {e}")
                return None

        # Dedicated channel for player damage to ensure it is always heard above the noise
        if sound_name in ['player_hit', 'player_death']:
            try:
                sound = self.sounds[sound_name]
                volume = self.volume_levels[sound_name]
                self.player_channel.set_volume(volume)
                print(f"♪ Playing player sound '{sound_name}' on DEDICATED player channel: {self.player_channel}, volume={volume:.2f} (GUARANTEED)")
                self.player_channel.play(sound)
                return self.player_channel
            except Exception as e:
                print(f"✗ Error playing player sound '{sound_name}': {e}")
                return None

        # Check debounce time if this sound has one configured
        if sound_name in self.debounce_times:
            current_time = time.time()
            debounce_duration = self.debounce_times[sound_name]

            if current_time - self.last_played_time.get(sound_name, 0) < debounce_duration:
                return None  # Too soon, skip this play

            self.last_played_time[sound_name] = current_time

        # Play sound on next available channel
        try:
            sound = self.sounds[sound_name]
            volume = self.volume_levels[sound_name]
            sound.set_volume(volume)

            # If it's a shoot sound, don't force a channel (let it drop if busy)
            # If it's anything else (like enemy death), force a channel to ensure it plays
            force_channel = (sound_name != 'shoot')
            channel = pygame.mixer.find_channel(force_channel)

            if channel:
                print(f"♪ Playing '{sound_name}' on channel: {channel}, volume={volume:.2f}, sound exists={sound is not None}")
                channel.play(sound)
                print(f"✓ Channel.play() called, channel is now busy: {channel.get_busy()}")
                return channel
            else:
                print(f"⚠ No available channels to play: {sound_name}")
                return None

        except Exception as e:
            print(f"✗ Error playing sound '{sound_name}': {e}")
            return None

    def set_volume(self, sound_name: str, volume: float) -> None:
        """
        Update the volume for a specific sound.

        Args:
            sound_name: Name of the sound to adjust
            volume: Volume level (0.0 to 1.0)
        """
        if sound_name not in self.sounds:
            print(f"⚠ Sound not found: {sound_name}")
            return

        volume = max(0.0, min(1.0, volume))  # Clamp to 0-1
        self.volume_levels[sound_name] = volume
        print(f"♪ Volume adjusted: {sound_name} → {volume:.1%}")

    def stop_all(self) -> None:
        """Stop all currently playing sounds."""
        pygame.mixer.stop()

    def set_master_volume(self, volume: float) -> None:
        """
        Set the master volume for the entire mixer.

        Args:
            volume: Master volume level (0.0 to 1.0)
        """
        volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(volume)
        print(f"🔊 Master volume set to: {volume:.1%}")

    def get_available_channels(self) -> int:
        """Return the number of available mixer channels."""
        return len([ch for ch in pygame.mixer.channels if not ch.get_busy()])


# Example usage:
if __name__ == "__main__":
    # Configure your sounds here - all mp3s in soundeffects folder
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

    # Initialize singleton
    sound_manager = SoundManager.get_instance()
    sound_manager.__init__(SOUNDS_CONFIG)  # Initialize with config

    # Test plays (uncomment to test once sounds are added)
    # sound_manager.play('shoot')
    # sound_manager.play('enemy_hit')
    # sound_manager.set_volume('shoot', 0.5)
