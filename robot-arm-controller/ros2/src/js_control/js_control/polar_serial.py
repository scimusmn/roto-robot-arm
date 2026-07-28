import rclpy
from rclpy.node import Node
from control_msgs.msg import JointJog
from std_srvs.srv import Trigger
from xarm_msgs.srv import SetInt16, MoveVelocity, Call, SetDigitalIO
from xarm_msgs.msg import RobotMsg
import time
import threading
import math
import serial
import serial.tools.list_ports


PITCH_DOWN = 0
PITCH_UP = -3.0000/2


GPIO_VACUUM = 3
GPIO_VALVE = 4


# r1 = 391.37
# r2 = 449.66
# 
# r1 = r1/r1
# r2 = r2/r1
# a2 = 0.340339 # 19.5 degrees

r1 = 1
r2 = 1
a2 = 0


MAX_SPEED = 3.1415/2


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
	u += a2
	if dr == 0 and dz == 0:
		return [ 0, 0 ]
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


def solve_angles_offset(u, v, dr, dz):
	c1 = r1*math.cos(u)
	c2 = r2*math.cos(v-u+a2)
	s1 = r1*math.sin(u)
	s2 = r2*math.sin(v-u+a2)

	dc = c1 - c2
	ds = -s1 + s2
	dv = (dz*dc)/(ds*dr - (c2*ds + dc*s2))
	du = (dr - c2*dv)/dc
	return [ angle_clamp(du), angle_clamp(dv) ]



def sign(x):
	if x < 0:
		return -1
	elif x > 0:
		return 1
	else:
		return 0

def zp_sign(x):
	if x < 0:
		return -1
	else:
		return 1



######## SERVICES ########

class Service():
	def __init__(self, node, path, type):
		self.node = node
		self.client_path = path
		self.client = node.create_client(type, path)
		self.future = None
		self._kwargs = {}
	
	def waitForService(self):
		result = self.client.wait_for_service(timeout_sec=1.0)	
		if not result:
			self.node.get_logger().info("waiting for %s" % self.client_path)
		else:
			self.node.get_logger().info("acquired service %s" % self.client_path)
		return result
	
	def msg(self, kwargs):
		raise Exception('child service did not implement msg()!')
	def rx(self, kwargs, result):
		pass
	
	def __call__(self, **kwargs):
		self._kwargs = kwargs
		self.future = self.client.call_async(self.msg(kwargs))
		return self.wait()

	def wait(self):
		if self.future == None:
			yield True
		while not self.future.done():
			yield False
		self.rx(self._kwargs, self.future.result())
		self.future = None
		yield True


class CleanErrorService(Service):
	def __init__(self, node):
		super().__init__(node, '/ufactory/clean_error', Call)
	def msg(self, kwargs):
		return Call.Request()
	def rx(self, kwargs, result):
		self.node.get_logger().info("cleared error")


class SetModeService(Service):
	def __init__(self, node):
		super().__init__(node, '/ufactory/set_mode', SetInt16)
	def msg(self, kwargs):
		req = SetInt16.Request()
		req.data = kwargs["mode"]
		return req
	def rx(self, kwargs, result):
		self.node.get_logger().info("set mode to %d (code %d)" % (kwargs['mode'], result.ret))


class SetStateService(Service):
	def __init__(self, node):
		super().__init__(node, '/ufactory/set_state', SetInt16)
	def msg(self, kwargs):
		req = SetInt16.Request()
		req.data = kwargs['state']
		return req
	def rx(self, kwargs, result):
		self.node.get_logger().info("set state to %d (code %d)" % (kwargs['state'], result.ret))


class SetTGPIODigitalService(Service):
	def __init__(self, node):
		super().__init__(node, '/ufactory/set_tgpio_digital', SetDigitalIO)
	def msg(self, kwargs):
		req = SetDigitalIO.Request()
		req.ionum = kwargs['pin']
		req.value = kwargs['value']
		return req
	def rx(self, kwargs, result):
		self.node.get_logger().info("set TGPIO pin %d to %d (code %d)" % (kwargs['pin'], kwargs['value'], result.ret))


class SetJointVelocityService(Service):
	def __init__(self, node):
		super().__init__(node, '/ufactory/vc_set_joint_velocity', MoveVelocity)
	def msg(self, kwargs):
		req = MoveVelocity.Request()
		req.speeds = kwargs['vels']
		return req
	def rx(self, kwargs, result):
		pass
		# self.node.get_logger().info("set joint velocities to %s (code %d)" % (str(kwargs['vels']), result.ret))



######## SUBSCRIPTIONS ########

class RobotState():
	def __init__(self, node):
		self.sub = node.create_subscription(
			RobotMsg,
			'/ufactory/robot_states',
			self.callback,
			10
		)

		self.error = 0
		self.angles = [ 0 for i in range(6) ]
		self.ready = False
	
	def callback(self, msg):
		self.error = msg.err
		self.angles = msg.angle
		x, y, z, roll, pitch, yaw = msg.pose	
		theta = math.atan2(y, x)
		r = math.sqrt(x*x + y*y)
		if self.ready:
			ts = time.time()
			dt = ts - self.ts
			self.ts = ts
			self.dtheta = (theta - self.theta)/dt
			self.dr = (r - self.r)/dt
			self.dz = (z - self.z)/dt
		else:
			self.ready = True
			self.ts = time.time()
		self.theta = theta
		self.r = r
		self.z = z
		self.pitch = pitch


class Button():
	def __init__(self, joy, num, press, release):
		self.joy = joy
		self.num = num
		self.press = press
		self.release = release
		self.state = False
	
	def update(self):
		state = self.joy.get_button(self.num)
		if (state != self.state):
			if state:
				self.press()
			else:
				self.release()
		self.state = state

class ToggleButton(Button):
	def __init__(self, joy, num, cbA, cbB):
		super().__init__(joy, num, self.press, lambda *args: None)
		self.cbA = cbA
		self.cbB = cbB
		self.toggle = True
	
	def press(self):
		if self.toggle:
			self.cbA()
		else:
			self.cbB()
		self.toggle = not self.toggle
		


class JsController(Node):
	def __init__(self, portname):
		super().__init__('js_publisher')
	
		# create service clients and subscribers
		self.robotState = RobotState(self)
		self.cleanError = CleanErrorService(self)
		self.setMode = SetModeService(self)
		self.setState = SetStateService(self)
		self.setGpio = SetTGPIODigitalService(self)
		self.setJointVelocity = SetJointVelocityService(self)

		# open serial port
		self.port = serial.Serial(portname, 115200)
		self.port.readline() # flush first line

		self.running = True
		self.rosUpdate = self.rosUpdateGen()

		self.inputTimestamp = time.time()
			
		self.dtheta = 0
		self.dr = 0
		self.dz = 0
		self.velSigns = [ 0, 0, 0 ]
		self.targetPitch = PITCH_UP
		
		self.limits = [
			(-3.1415/2, 3.1415/2), # theta
			(300, 612), # r
			(433, 900), # z
		]

		self.goHome = False
	
	def gripperStart(self):
		self.setGpio(pin=GPIO_VACUUM, value=1)
		self.setGpio(pin=GPIO_VALVE, value=0)
	
	def gripperStop(self):
		self.setGpio(pin=GPIO_VACUUM, value=0)
	
	def gripperDrop(self):
		self.setGpio(pin=GPIO_VALVE, value=1)
	

	def moveToPosition(self, theta, r, z):
		self.targetPitch = PITCH_UP
		dtheta = 0
		dr = 0
		dz = 0
		if abs(self.robotState.theta - theta) > 0.10:
			dtheta = -0.5 * sign(self.robotState.theta - theta)
		if abs(self.robotState.r - r) > 5:
			dr = 0.5 * sign(self.robotState.r - r)
		if abs(self.robotState.z - z) > 5:
			dz = -0.5 * sign(self.robotState.z - z)
		if self.goHome and dtheta == 0 and dr == 0 and dz == 0:
			self.goHome = False
		return self.setVelocities(dtheta, dr, dz)
		
	
	
	def setVelocities(self, dtheta, dr, dz):
		vels = [ 0 for i in range(6) ]

		# block bad velocities
		if self.velSigns[0] != 0:
			if sign(dtheta) != self.velSigns[0]:
				dtheta = 0
			else:
				self.velSigns[0] = 0
		if self.velSigns[1] != 0:
			if sign(dr) != self.velSigns[1]:
				dr = 0
			else:
				self.velSigns[1] = 0
		if self.velSigns[2] != 0:
			if sign(dz) != self.velSigns[2]:
				dz = 0
			else:
				self.velSigns[2] = 0

		# block limits
		def slowNear(v, x, lim, sgn, scale=10):
			diff = sgn * (lim - x) / scale 
			diff = clamp(diff, -1, 1)
			return diff

		def limitSlow(v, x, lim, scale=10):
			lo, hi = lim
			slowLo = slowNear(v, x, lo, -1, scale)
			slowHi = slowNear(v, x, hi,  1, scale)
			return slowLo * slowHi

		def testLimit(v, x, lim, scale=10):
			lo, hi = lim
			f = limitSlow(v, x, lim, scale)
			# if x < lo and v < 0:
			if x < lo:
				return -f
			elif x > hi:
				return f
			else:
				midpoint = (lo+hi)/2
				if x > midpoint and v > 0:
					return f*v
				elif x < midpoint and v < 0:
					return f*v
				else:
					return v

		dtheta = testLimit(
			dtheta, 
			self.robotState.theta, 
			self.limits[0],
			0.1
		)
		dr = -testLimit(-dr, self.robotState.r, self.limits[1])
		dz = testLimit(dz, self.robotState.z, self.limits[2])

		# save velocities
		self.dtheta = dtheta
		self.dr = dr
		self.dz = dz

		if self.robotState.ready:
			def error(s, r):
				if r != 0:
					return s-r
				else:
					return 0
			ez = error(self.dz, self.robotState.dz)
			er = error(self.dr, self.robotState.dr)
			etheta = error(self.dtheta, self.robotState.dtheta)
			# dz = dz - ez
			# dr = dr - er
			# dtheta = dtheta - etheta



		# compute joint velocities
		a1 = self.robotState.angles[1]
		a2 = self.robotState.angles[2]
		v1, v2 = solve_angles(a1, a2, 0.1*dr, 0.1*dz)
		# v1, v2 = solve_angles_offset(a1, a2, 0.1*dr, 0.1*dz)
		vels[0] = 0.1*dtheta
		vels[1] = v1
		vels[2] = v2
		if abs(self.robotState.pitch - self.targetPitch) > 0.10:
			vels[4] = 0.5*sign(self.robotState.pitch - self.targetPitch)
		vels[4] += v2 - v1
		if self.robotState.pitch < -3.1415/2:
			vels[4] = 0

		return self.setJointVelocity(vels=vels)
	
	def setVelocityBurst(self, dtheta, dr, dz, frames):
		wait = self.setVelocities(dtheta, dr, dz)
		while not next(wait):
			yield False
		for i in range(frames):
			yield False
		yield True
	

	def setVelocitiesFromJoystick(self, dtheta, dr, dz):
		# parameters
		center = 460
		span = 300
		dead = 0.20

		# adjust raw ADC value to level
		dtheta = (dtheta - center) / span 
		dr = -(dr - center) / span
		dz = (dz - center) / span

		# zero dead zone 
		if abs(dtheta) < dead:
			dtheta = 0
		if abs(dr) < dead:
			dr = 0
		if abs(dz) < dead:
			dz = 0

		if dtheta != 0 or dr != 0 or dz != 0:
			self.inputTimestamp = time.time()
		idleTime = time.time() - self.inputTimestamp
		if self.goHome or idleTime > 10:
			return self.moveToPosition(0, 400, 500)
		else:
			return self.setVelocities(dtheta, dr, dz)

	

	def configureVelocityMode(self):
		wait = self.setMode(mode=4)
		while not next(wait):
			yield False
		wait = self.setState(state=0)
		while not next(wait):
			yield False
		yield True
	
	def blockAndClearError(self):
		vels = [ self.dtheta, self.dr, self.dz ]
		self.velSigns = [ -sign(v) for v in vels ]
		wait = self.cleanError()
		while not next(wait):
			yield False
		wait = self.configureVelocityMode()
		while not next(wait):
			yield False
		yield True
	
	def clearErrorAndReverse(self):
		wait = self.cleanError()
		while not next(wait):
			yield False
		wait = self.configureVelocityMode()
		while not next(wait):
			yield False
		wait = self.setVelocityBurst(-self.dtheta, -self.dr, -self.dz, 5)
		while not next(wait):
			yield False
		yield True
	

	def rosUpdateGen(self):
		yield
		# wait for service clients to be ready
		srvs = [ 
			self.cleanError, 
			self.setMode, self.setState, 
			self.setGpio, self.setJointVelocity,
		]
		def wait_ready():
			for srv in srvs:
				if not srv.waitForService():
					return False
			return True
		while not wait_ready():
			self.get_logger().info("waiting for services...")
			yield


		# configure robot mode
		wait = self.configureVelocityMode()
		while not next(wait):
			yield

		self.setGpio(pin=4, value=0)

		# main loop
		while True:
			# print(
			# 	self.robotState.dr, 
			# 	self.robotState.dz,
			# 	self.robotState.dtheta
			# )
			line = self.port.readline()
			linearr = line.decode().strip().split(' ')
			linearr = [ int(x) for x in linearr ]
			dtheta, dr, dz, bup, bdown, tgt1, tgt2, tgt3 = linearr
			print(linearr)

			if self.robotState.z and self.targetPitch == 0 < 500:
				self.gripperStart()
			else:
				self.gripperStop()

			if bup > 0:
				self.targetPitch = PITCH_UP
				self.inputTimestamp = time.time()
			if bdown > 0:
				self.targetPitch = PITCH_DOWN 
				self.inputTimestamp = time.time()

			if tgt1 > 0 or tgt2 > 0 or tgt3 > 0:
				self.gripperDrop()
				self.goHome = True

			wait = None
			if self.robotState.error == 22: # self-collision
				wait = self.blockAndClearError()
			elif self.robotState.error == 23: # joint limit
				wait = self.clearErrorAndReverse()
			elif self.robotState.error == 35: # safety boundary
				wait = self.clearErrorAndReverse()
			else:
				wait = self.setVelocitiesFromJoystick(dtheta, dr, dz)
			while not next(wait):
				yield

		
		

	def update(self):
		next(self.rosUpdate)
		rclpy.spin_once(self)
	

def main(args=None):
	print("finding serial js...")
	ports = serial.tools.list_ports.comports()
	port = None
	for p in ports:
		if p.vid == 0x10c4 and p.pid == 0xea60:
			port = p.device
			break
	if port == None:
		print("not found!")
		return
	print("found!")

	rclpy.init(args=args)
	node = JsController(port)
	while node.running:
		try:
			node.update()
		except KeyboardInterrupt:
			break	
	node.destroy_node()
	rclpy.shutdown()



if __name__ == "__main__":
	main()
