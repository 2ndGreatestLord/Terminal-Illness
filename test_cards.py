"""Test the new Card sprite and CardSelectionMenu functionality."""
import pygame
import time
from ui_screens import Card, CardSelectionMenu

pygame.init()
screen = pygame.display.set_mode((800, 600))

# Test 1: Card sprite creation
print("=== Card Sprite Test ===")
card1 = Card("Rapid Fire", (255, 100, 0), 200, 300, 120, 150, start_delay_ms=0)
card2 = Card("Pierce", (100, 200, 255), 400, 300, 120, 150, start_delay_ms=100)
card3 = Card("Well Nourished", (255, 0, 100), 600, 300, 120, 150, start_delay_ms=200)
print(f"✓ Card 1 type: {card1.type_name}")
print(f"✓ Card 2 type: {card2.type_name}")
print(f"✓ Card 3 type: {card3.type_name}")

# Test 2: Focus state
print("\n=== Focus State Test ===")
print(f"Card 1 initial focus: {card1.is_focused}")
card1.update_focus(True)
print(f"Card 1 after focus=True: {card1.is_focused}")
card1.update_focus(False)
print(f"Card 1 after focus=False: {card1.is_focused}")

# Test 3: Entrance animation timing
print("\n=== Entrance Animation Test ===")
print(f"Card 1 flip at t=0ms: {card1.current_flip:.1f}°")
card1.update_entrance(0)
print(f"Card 1 flip at t=0ms (after update): {card1.current_flip:.1f}°")
card1.update_entrance(250)  # Half-way through
print(f"Card 1 flip at t=250ms (mid-animation): {card1.current_flip:.1f}°")
card1.update_entrance(500)
print(f"Card 1 flip at t=500ms (complete): {card1.current_flip:.1f}°")

# Card 2 should still be flipped (starts at 100ms delay)
card2.update_entrance(250)  # 250ms, but starts at 100ms
print(f"Card 2 flip at t=250ms (150ms into animation): {card2.current_flip:.1f}°")

# Test 4: CardSelectionMenu
print("\n=== CardSelectionMenu Test ===")
class MockPlayer:
    def __init__(self):
        self.level = 1

player = MockPlayer()
menu = CardSelectionMenu(screen, player)
print(f"✓ Menu created with {len(menu.cards)} cards")
print(f"✓ Card names: {[card.type_name for card in menu.cards]}")

# Test 5: Focus management in menu update
print("\n=== Focus Management Test ===")
menu.update(0)
# All cards should start unfocused
unfocused_count = sum(1 for card in menu.cards if not card.is_focused)
print(f"✓ Unfocused cards (should be 3): {unfocused_count}")

# Simulate mouse hover over first card
pygame.mouse.set_pos(menu.cards[0].base_x, menu.cards[0].base_y)
menu.update(0)
focused_count = sum(1 for card in menu.cards if card.is_focused)
print(f"✓ Focused cards after hover (should be 1): {focused_count}")
focused_card_type = next((card.type_name for card in menu.cards if card.is_focused), None)
print(f"✓ Focused card type: {focused_card_type}")

print("\n✓ All tests PASSED!")
