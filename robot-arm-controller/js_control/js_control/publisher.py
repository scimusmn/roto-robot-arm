import rclpy
from rclpy.node import Node
from control_msgs.msg import JointJog
from std_srvs.srv import Trigger
from xarm_msgs.srv import SetInt16, MoveVelocity
from xarm_msgs.msg import RobotMsg
import threading
import pygame


class JsController(Node):
	def __init__(self):
		super().__init__('js_publisher')

		self.robot_state = self.create_subscription(
			RobotMsg, 
			'/ufactory/robot_states',
			self.robot_state_callback,
			10
		)

		self.futures = []
		self.set_mode_srv = self.create_client(SetInt16, '/ufactory/set_mode')
		self.set_state_srv = self.create_client(SetInt16, '/ufactory/set_state')
		self.set_cartesian_velocity_srv = self.create_client(MoveVelocity, '/ufactory/vc_set_cartesian_velocity')

		while not self.all_services_ready((
			self.set_mode_srv,
			self.set_state_srv,
		)):
			self.get_logger().info("waiting for services...")

		#self.timer = self.create_timer(0.01, self.publish_ax1)
		#self.servo_start = self.create_client(Trigger, '/servo_server/start_servo')
		#self.servo_start.wait_for_service(timeout_sec=1.0)
		#self.servo_start.call_async(Trigger.Request())
	
	def robot_state_callback(self, msg):
		self.get_logger().info('error: %d' % msg.err)
	
	def all_services_ready(self, srvs):
		for srv in srvs:
			if not srv.wait_for_service(timeout_sec=1.0):
				return False
		return True
	

	def call_service(self, fn, args):
		self.futures.append(fn(args))

	def futures_complete(self):
		not_complete = False
		for (future, cb) in self.futures:
			if future.done():
				cb(future)
			else:
				not_complete = True
		self.futures = [ (future, cb) for (future, cb) in self.futures if not future.done() ]
		return not not_complete

	
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
	

	def set_cartesian_velocity(self, args):
		msg = MoveVelocity.Request()
		msg.speeds = [ x for x in args ]
		future = self.set_cartesian_velocity_srv.call_async(msg)
		def cb(future):
			self.get_logger().info("set velocity to %s" % (str(args)))
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


def pygame_main(node):
	control_map = [
		# js_axis, vel_axis, invert, subtract
		(1, 2, True, False),
		(2, 1, True, False),
		(3, 0, True, False),
	]
	pygame.init()
	screen = pygame.display.set_mode((640, 480))
	clock = pygame.time.Clock()
	running = True
	
	pygame.joystick.init()
	joy = pygame.joystick.Joystick(1)
	
	
	while running:
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False
		
		vel = [0, 0, 0,     0, 0, 0]
		for control in control_map:
			j_axis, v_axis, invert, subtract = control
			v = joy.get_axis(j_axis)
			if abs(v) < 0.1:
				v = 0
			if subtract:
				v = (v+1)/2
			if invert:
				v = -v
			vel[v_axis] += 60*v
		print(len(node.futures))
		if node.futures_complete():
			node.call_service(node.set_cartesian_velocity, vel)

		rclpy.spin_once(node)

		# 
		# screen.fill('purple')
		# pygame.display.flip()
		clock.tick(60)
	
	pygame.quit()





def main(args=None):
	rclpy.init(args=args)
	node = JsController()
	node.call_service(node.set_mode, (5,))
	node.call_service(node.set_state, (0,))
	try:
		pygame_main(node)
	except KeyboardInterrupt:
		pass
	node.destroy_node()
	rclpy.shutdown()


if __name__ == "__main__":
	main()
