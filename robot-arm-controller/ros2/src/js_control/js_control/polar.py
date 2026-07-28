import rclpy
from rclpy.node import Node
from control_msgs.msg import JointJog
from std_srvs.srv import Trigger
from xarm_msgs.srv import SetInt16, MoveVelocity, Call, SetDigitalIO
from xarm_msgs.msg import RobotMsg
import threading
import pygame
import math


r1 = 1
r2 = 1
# r1 = 0.381
# r2 = 0.731


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
	
	def callback(self, msg):
		self.error = msg.err
		self.angles = msg.angle
		x, y, z, roll, pitch, yaw = msg.pose	
		self.theta = math.atan2(y, x)
		self.r = math.sqrt(x*x + y*y)
		print('r', self.r)
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
	def __init__(self, jsIndex=0):
		super().__init__('js_publisher')
	
		# create service clients and subscribers
		self.robotState = RobotState(self)
		self.cleanError = CleanErrorService(self)
		self.setMode = SetModeService(self)
		self.setState = SetStateService(self)
		self.setGpio = SetTGPIODigitalService(self)
		self.setJointVelocity = SetJointVelocityService(self)

		# create pygame instance
		pygame.init()
		self.pg_screen = pygame.display.set_mode((640, 480))
		pygame.joystick.init()
		self.joy = pygame.joystick.Joystick(jsIndex)
		self.pg_clock = pygame.time.Clock()
		self.running = True
		self.rosUpdate = self.rosUpdateGen()
		
		# create buttons
		self.vacuumButton = ToggleButton(
			self.joy, 0, 
			lambda : self.setGpio(pin=3, value=1),
			lambda : self.setGpio(pin=3, value=0),
		)
		self.dropButton = Button(
			self.joy, 1,
			lambda : self.setGpio(pin=4, value=1),
			lambda : self.setGpio(pin=4, value=0),
		)
		def setPitch(p):
			self.targetPitch = p
		self.pitchButton = ToggleButton(
			self.joy, 3,
			lambda : setPitch(-3.1415/2),
			lambda : setPitch(0),
		)
		
		self.dtheta = 0
		self.dr = 0
		self.dz = 0
		self.velSigns = [ 0, 0, 0 ]
		self.targetPitch = 0
		
		self.limits = [
			(-3.1415/2, 3.1415/2), # theta
			(300, 597), # r
			(440, 1000), # z
		]
	
	
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
		def testLimit(v, x, lim):
			lo, hi = lim
			if x < lo and v < 0:
				return 0
			elif x > hi and v > 0:
				return 0
			else:
				return v

		dtheta = testLimit(dtheta, self.robotState.theta, self.limits[0])
		dr = -testLimit(-dr, self.robotState.r, self.limits[1])
		dz = testLimit(dz, self.robotState.z, self.limits[2])

		# save velocities
		self.dtheta = dtheta
		self.dr = dr
		self.dz = dz

		# compute joint velocities
		a1 = self.robotState.angles[1]
		a2 = self.robotState.angles[2]
		v1, v2 = solve_angles(a1, a2, 0.1*dr, 0.1*dz)
		vels[0] = 0.1*dtheta
		vels[1] = v1
		vels[2] = v2
		if abs(self.robotState.pitch - self.targetPitch) > 0.10:
			vels[4] = 0.5*sign(self.robotState.pitch - self.targetPitch)
		vels[4] += v2 - v1

		return self.setJointVelocity(vels=vels)
	
	def setVelocityBurst(self, dtheta, dr, dz, frames):
		wait = self.setVelocities(dtheta, dr, dz)
		while not next(wait):
			yield False
		for i in range(frames):
			yield False
		yield True
	

	def setVelocitiesFromJoystick(self):
		# read joystick
		dtheta = -self.joy.get_axis(2)
		dr =  self.joy.get_axis(1)
		dz = -self.joy.get_axis(3)

		# zero dead zone 
		if abs(dtheta) < 0.1:
			dtheta = 0
		if abs(dr) < 0.1:
			dr = 0
		if abs(dz) < 0.1:
			dz = 0

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
			self.vacuumButton.update()
			self.dropButton.update()
			self.pitchButton.update()
			wait = None
			if self.robotState.error == 22: # self-collision
				wait = self.blockAndClearError()
			elif self.robotState.error == 23: # joint limit
				wait = self.clearErrorAndReverse()
			elif self.robotState.error == 35: # safety boundary
				wait = self.clearErrorAndReverse()
			else:
				wait = self.setVelocitiesFromJoystick()
			while not next(wait):
				yield

		
		

	def update(self):
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				self.running = False

		next(self.rosUpdate)
		rclpy.spin_once(self)
		self.pg_screen.fill('purple')
		pygame.display.flip()
		self.pg_clock.tick(60)
	

def main(args=None):
	rclpy.init(args=args)
	node = JsController()
	while node.running:
		try:
			node.update()
		except KeyboardInterrupt:
			break	
	pygame.quit()
	node.destroy_node()
	rclpy.shutdown()



if __name__ == "__main__":
	main()
