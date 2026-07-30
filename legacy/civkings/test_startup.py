import sys
sys.path.insert(0, '.')

import pygame
pygame.init()
pygame.display.set_mode((1024, 768))

from pygame_app.app import GameApp
app = GameApp()

from pygame_app.screens.new_game_dialog import NewGameDialog
app.register_screen('new_game_dialog', NewGameDialog(app))
app.switch_screen('new_game_dialog')
app._current_screen._start_game()

gs = app._current_screen
gs.update(0.033)
app.screen.fill((10, 11, 13))
gs.draw(app.screen)

pygame.display.flip()
print('RENDER OK')
pygame.quit()
