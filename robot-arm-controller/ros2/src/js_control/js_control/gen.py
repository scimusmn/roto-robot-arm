#!/usr/bin/env python3

import math
import numpy as np
import matplotlib.pyplot as pt


r1 = 1
r2 = 1


MAX_SPEED = 100*3.1415


def clamp(x, lo, hi):
	if x < lo:
		return lo
	elif x > hi:
		return hi
	else:
		return x

def angle_clamp(x):
	return clamp(x, -MAX_SPEED, MAX_SPEED)


def solve_angles(u, v, dr, dz):
	a = r1*math.sin(u)
	A = r1*math.cos(u)
	b = r2*math.sin(v-u)
	B = r2*math.cos(v-u)

	# du = ((dr/B)-(dz/b)) / ((a/b)+(A/B))
	if a*B + A*b == 0:
		return solve_angles(u, v+0.01, dr, dz)

	du = b*dr - B*dz
	du /= a*B + A*b

	dv = (dr/B) - (A/B - 1)*du
	# return [ du, dv ]
	return [ angle_clamp(du), angle_clamp(dv) ]



def solve_trajectory(dr, dz, N=100, T=1):
	dt = T/N
	t = [ i*dt for i in range(N) ]
	dU = []
	dV = []
	u = 0
	v = 0
	U = []
	V = []
	for _ in t:
		du, dv = solve_angles(u, v, dr, dz)	
		u += dt*du
		v += dt*dv
		dU.append(du)
		dV.append(dv)
		U.append(u)
		V.append(v)
	return np.array(t), np.array(U), np.array(V), np.array(dU), np.array(dV)
		


t, u, v, dU, dV = solve_trajectory(1, 0, 1000)
print(u, v)
delta1 = 0
delta2 = 1
r = (r1+delta1)*np.sin(u) + (r2+delta2)*np.sin(v - u)
z = (r1+delta1)*np.cos(u) - (r2+delta2)*np.cos(v - u)
pt.plot(t, r, label='r')
pt.plot(t, z, label='z')
pt.legend()
pt.show()

pt.plot(t, u, label='u')
pt.plot(t, v, label='v')
pt.plot(t, dU, label='u\'')
pt.plot(t, dV, label='v\'')
pt.legend()
# pt.plot(t, dU)
# pt.plot(t, dV)
pt.show()
