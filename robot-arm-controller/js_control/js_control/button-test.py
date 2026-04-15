#!/usr/bin/env python3

import pygame

pygame.init()
pygame.joystick.init()
screen = pygame.display.set_mode((640, 480))
joy = pygame.joystick.Joystick(1)
clock = pygame.time.Clock()


while True:
	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			self.running = False
	print('--------')
	for i in range(joy.get_numbuttons()):
		print(i, joy.get_button(i))
	screen.fill('purple')
	pygame.display.flip()
	clock.tick(60)
