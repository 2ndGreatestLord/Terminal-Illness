import random
import pygame


class WaveManager:
	def __init__(self):
		self.current_wave = 0
		self.enemies_spawned_this_wave = 0
		self.wave_active = False
		self.is_boss_wave = False
		self.wave_budget = 0

		# Boss wave timing
		self.boss_wave_start_time = None
		self.boss_spawn_delay_ms = 8000  # 8 seconds before boss spawns
		self.boss_spawned = False
		self.boss_group = None
		self.bosses_alive = 0

	def start_next_wave(self):
		self.current_wave += 1
		self.enemies_spawned_this_wave = 0
		self.wave_active = True
		# Aggressive progression: significantly more enemies every wave.
		self.wave_budget = 20 + (self.current_wave * 12) + int((self.current_wave ** 2) * 0.8)
		self.is_boss_wave = self.current_wave in (10, 20)

		# Boss waves pause regular spawning; the caller can spawn boss content instead.
		if self.is_boss_wave:
			self.wave_budget = 0
			self.boss_wave_start_time = pygame.time.get_ticks()
			self.boss_spawned = False
			self.bosses_alive = 0

	@property
	def enemies_spawned(self):
		return self.enemies_spawned_this_wave

	def _available_enemy_types(self):
		if self.current_wave <= 3:
			return ["Virus"]
		if self.current_wave <= 6:
			return ["Virus", "Stalker"]
		return ["Virus", "Stalker", "Tank"]

	def get_enemy_type(self):
		"""Return an enemy type string based on wave composition rules."""
		if self.current_wave <= 3:
			return "Virus"

		if self.current_wave <= 6:
			# Mid-game: mostly Virus with some Stalkers.
			return random.choices(["Virus", "Stalker"], weights=[70, 30], k=1)[0]

		# Late game: introduce Tanks while preserving a Virus majority.
		# Slightly increase Tank chance every few waves.
		tank_weight = min(30, 10 + (self.current_wave - 7) * 2)
		stalker_weight = min(35, 25 + (self.current_wave - 7))
		virus_weight = max(35, 100 - tank_weight - stalker_weight)
		return random.choices(
			["Virus", "Stalker", "Tank"],
			weights=[virus_weight, stalker_weight, tank_weight],
			k=1,
		)[0]

	def can_spawn_more(self):
		"""True if this non-boss wave still has budget left for regular enemies."""
		return self.wave_active and not self.is_boss_wave and self.enemies_spawned_this_wave < self.wave_budget

	def mark_enemy_spawned(self):
		self.enemies_spawned_this_wave += 1

	def end_wave(self):
		self.wave_active = False

	def update_wave_state(self, enemies_alive):
		"""Auto-end regular waves once budget is spent and all spawned enemies are gone."""
		if not self.wave_active:
			return

		# For boss waves, check if all bosses are dead
		if self.is_boss_wave:
			self.bosses_alive = enemies_alive
			if self.boss_spawned and enemies_alive <= 0:
				self.wave_active = False
			return

		# Regular waves
		if self.enemies_spawned_this_wave >= self.wave_budget and enemies_alive <= 0:
			self.wave_active = False

	def should_spawn_boss(self):
		"""Check if it's time to spawn the boss (after 8-second delay)."""
		if not self.is_boss_wave or self.boss_spawned or self.boss_wave_start_time is None:
			return False

		elapsed = pygame.time.get_ticks() - self.boss_wave_start_time
		return elapsed >= self.boss_spawn_delay_ms

	def get_boss_spawn_info(self, screen_rect=None):
		"""Return spawn position(s) based on wave number.
		Wave 10: Single boss at top-center, off-map
		Wave 20: Two bosses at top-left and top-right, off-map
		"""
		self.boss_spawned = True
		if screen_rect is None:
			screen_rect = pygame.Rect(0, 0, 800, 600)  # Default fallback

		# Spawn bosses well off-map to account for boss radius (70) + minion offset (200)
		spawn_distance = 300  # Ensure bosses and minions spawn well off-map

		if self.current_wave == 10:
			# Spawn at top-center, off-map
			return [(screen_rect.centerx, -spawn_distance)]
		elif self.current_wave == 20:
			# Spawn at specific corners
			W, H = screen_rect.width, screen_rect.height
			return [(W // 8, H // 8), (7 * W // 8, 7 * H // 8)]
		return []

	def get_boss_countdown_ms(self):
		"""Return milliseconds remaining until boss spawns (for UI display)."""
		if not self.is_boss_wave or self.boss_wave_start_time is None:
			return 0
		elapsed = pygame.time.get_ticks() - self.boss_wave_start_time
		remaining = max(0, self.boss_spawn_delay_ms - elapsed)
		return remaining

	def get_spawn_delay(self):
		"""Milliseconds between spawns; decreases with wave for a more frantic pace."""
		# Faster baseline to support high-density waves.
		return max(120, 900 - (self.current_wave * 55))

	def get_spawn_batch_size(self):
		"""How many enemies to spawn per spawn tick."""
		return min(6, 1 + (self.current_wave // 4))

	def get_alive_enemy_cap(self):
		"""Adaptive cap to avoid runaway frame drops with very high budgets."""
		return min(220, 80 + (self.current_wave * 12))
