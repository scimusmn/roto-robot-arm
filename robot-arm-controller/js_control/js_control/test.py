#!/usr/bin/env python3


class Parent():
	def fn(self):
		print('hello from parent!')
	def call(self):
		self.fn()


class Child(Parent):
	def __init__(self):
		super().__init__()
	def fn(self):
		print('hello from child!')


c = Child()
c.call()
