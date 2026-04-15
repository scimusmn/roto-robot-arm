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


class Service:
	def __init__(self, node, type, path):
		self.srv = node.create_client(type, path)

	def wait_ready(self, timeout=1.0):
		if not self.srv.wait_for_service(timeout_sec=timeout):
			yield False
		yield True
	
	def __call__(self, args):
		msg = self.message(args)
		future = self.srv.call_async(msg)
		while not future.done():
			yield False
		yield True


class JointVelocitySrv(Service):
	def __init__(self):
		super.__init__()
	
	def message(args):
		msg = MoveVelocity.Request()



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

