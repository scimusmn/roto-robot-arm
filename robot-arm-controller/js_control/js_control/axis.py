import rclpy
from rclpy.node import Node
from control_msgs.msg import JointJog
from std_srvs.srv import Trigger
from xarm_msgs.srv import SetInt16, MoveVelocity, Call, SetDigitalIO
from xarm_msgs.msg import RobotMsg
import threading
import pygame


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


class RobotState():
	def __init__(self, node):
		self.sub = node.create_subscription(
			RobotMsg,
			'/ufactory/robot_states',
			self.callback,
			10
		)

		self.error = 0
		self.angle = [ 0 for i in range(6) ]
	
	def callback(self, msg):
		self.error = msg.err
		self.angle = msg.angle
	


		



class JsController(Node):
	def __init__(self):
		super().__init__('js_publisher')

		self.robot_state = self.create_subscription(
			RobotMsg, 
			'/ufactory/robot_states',
			self.robot_state_callback,
			10
		)
		self.resetting = False
		self.robot_err = 0
		self.vel = [ 0, 0, 0, 0, 0, 0 ]
		self.vel_blocks = [ 0 for i in range(6) ]
		self.vel_blocks_count = [ 0 for i in range(6) ]
		
		self.futures = []
		self.clean_error_srv = self.create_client(Call, '/ufactory/clean_error')
		self.set_mode_srv = self.create_client(SetInt16, '/ufactory/set_mode')
		self.set_state_srv = self.create_client(SetInt16, '/ufactory/set_state')
		self.set_joint_velocity_srv = self.create_client(MoveVelocity, '/ufactory/vc_set_joint_velocity')
		self.set_tgpio_digital_srv = self.create_client(SetDigitalIO, '/ufactory/set_tgpio_digital')
		
		while not self.all_services_ready((
			self.clean_error_srv,
			self.set_mode_srv,
			self.set_state_srv,
			self.set_tgpio_digital_srv,
		)):
			self.get_logger().info("waiting for services...")

		#self.timer = self.create_timer(0.01, self.publish_ax1)
		#self.servo_start = self.create_client(Trigger, '/servo_server/start_servo')
		#self.servo_start.wait_for_service(timeout_sec=1.0)
		#self.servo_start.call_async(Trigger.Request())
	

	def stop_moving_axes(self):
		self.vel_blocks = [ sign(v) for v in self.vel ]
	
		
	
	def robot_state_callback(self, msg):
		if self.resetting:
			return
		self.robot_err = msg.err
		self.get_logger().info("error: %d" % msg.err)
		if msg.err == 22: # self-collision
			self.vel_blocks = [ sign(v) for v in self.vel ]
			self.resetting = True
		if msg.err == 23: # joint limit
			self.vel_blocks = [ sign(v) for v in self.vel ]
			self.resetting = True
		if msg.err == 35: # safety boundary
			self.vel_blocks = [ sign(v) for v in self.vel ]
			self.resetting = True
			
		
	
	def all_services_ready(self, srvs):
		for srv in srvs:
			if not srv.wait_for_service(timeout_sec=1.0):
				return False
		return True
	

	def call_service(self, fn, args):
		f = fn(args)
		self.futures.append(f)
		return f[0]

	def check_futures(self):
		for (future, cb) in self.futures:
			if future.done():
				cb(future)
		self.futures = [ (future, cb) for (future, cb) in self.futures if not future.done() ]
	
	def clean_error(self, args):
		future = self.clean_error_srv.call_async(Call.Request())
		def cb(future):
			self.get_logger().info('cleared error')
		return (future, cb)

	
	def set_mode(self, args):
		(mode,) = args
		msg = SetInt16.Request()
		msg.data = mode
		future = self.set_mode_srv.call_async(msg)
		def cb(future):
			self.get_logger().info("mode set to %d" % (mode))
		return (future, cb)


	def set_state(self, args):
		(state,) = args
		msg = SetInt16.Request()
		msg.data = state 
		future = self.set_state_srv.call_async(msg)
		def cb(future):
			self.get_logger().info("state set to %d" % (state))
		return (future, cb)
	
	def _clean_vel(self, vels, i):
		if (self.vel_blocks[i] != 0) and sign(vels[i]) == self.vel_blocks[i]:
			return 0
		elif vels[i] != 0:
			self.vel_blocks[i] = 0
			return vels[i]
		else:
			return 0

	def set_joint_velocity(self, args):
		self.vel = [ self._clean_vel(args, i) for i in range(len(args)) ]
		print(args, self.vel, self.vel_blocks)
		msg = MoveVelocity.Request()
		msg.speeds = self.vel
		future = self.set_joint_velocity_srv.call_async(msg)
		def cb(future):
			self.get_logger().info("set velocity to %s" % (str(self.vel)))
		return (future, cb)

	
	def set_tgpio_digital(self, args):
		pin, value = args
		msg = SetDigitalIO.Request()
		msg.ionum = pin
		msg.value = value
		future = self.set_tgpio_digital_srv.call_async(msg)
		def cb(future):
			self.get_logger().info('set tgpio %s' % str(args))
		return (future, cb)



	def publish_ax1(self):
		self.get_logger().info("publishing to joint 1")
		self.publish([ ('joint1', -1) ])
	

	def publish(self, axis_vels):
		self.get_logger().info(str(axis_vels))
		msg = JointJog()
		for vel in axis_vels:
			msg.joint_names.append(vel[0])
			msg.velocities.append(vel[1])
		msg.header.frame_id = 'joint'
		msg.header.stamp = self.get_clock().now().to_msg()
		self.publisher.publish(msg)


class ToggleButton():
	def __init__(self, joy, btn, on, off):
		self.joy = joy
		self.btn = btn
		self.on = on
		self.off = off
		self.hold = False
		self.toggle = False
	
	def update(self):
		btn = self.joy.get_button(self.btn)
		if btn:
			if not self.hold:
				if self.toggle:
					self.toggle = False
					self.off()
				else:
					self.toggle = True
					self.on()
			self.hold = True
		else:
			self.hold = False



def pygame_main(node):
	pygame.init()
	screen = pygame.display.set_mode((640, 480))
	pygame.joystick.init()
	joy = pygame.joystick.Joystick(1)
	clock = pygame.time.Clock()

	control_map = [
		# js_axis, vel_axis, invert, subtract
		(1, 2, False, False),
		(3, 1, False, False),
		(2, 0, True, False),
		(4, 4, False, True),
		(5, 4, True, True),
	]

	def vacuum_on():
		node.call_service(node.set_tgpio_digital, (3, 1))
	def vacuum_off():
		node.call_service(node.set_tgpio_digital, (3, 0))
	def valve_on():
		node.call_service(node.set_tgpio_digital, (4, 1))
	def valve_off():
		node.call_service(node.set_tgpio_digital, (4, 0))
	vacuum_btn = ToggleButton(joy, 0, vacuum_on, vacuum_off)
	valve_btn = ToggleButton(joy, 1, valve_on, valve_off)
	
	running = True
	blocking_future = None
	
	
	while running:
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False
	
		if node.resetting and not blocking_future:
			blocking_future = node.call_service(node.clean_error, ())
	
		if blocking_future:
			rclpy.spin_once(node)
			if blocking_future.done():
				blocking_future = None
				node.call_service(node.set_mode, (4,))
				node.call_service(node.set_state, (0,))
				node.resetting = False
		# elif len(node.futures) == 0 and node.err_reset_frames == 0:
		else:
			valve_btn.update()
			vacuum_btn.update()

			vel = [ 0 for i in range(6) ]
			for control in control_map:
				j_axis, v_axis, invert, subtract = control
				v = joy.get_axis(j_axis)
				if abs(v) < 0.1:
					v = 0
				if subtract:
					v = (v+1)/2
				if invert:
					v = -v
				vel[v_axis] += 0.1*v
			vel[4] *= 2
			vel[4] += -vel[1] + vel[2]
			print(vel)
			node.call_service(node.set_joint_velocity, vel)


		rclpy.spin_once(node)
		node.check_futures()

			
		screen.fill('purple')
		pygame.display.flip()
		clock.tick(60)
	
	pygame.quit()





def main(args=None):
	rclpy.init(args=args)
	node = JsController()
	node.call_service(node.set_mode, (4,))
	node.call_service(node.set_state, (0,))
	try:
		pygame_main(node)
	except KeyboardInterrupt:
		pass
	node.destroy_node()
	rclpy.shutdown()


if __name__ == "__main__":
	main()
