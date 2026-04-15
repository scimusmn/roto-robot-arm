import rclpy
from rclpy.node import Node
from control_msgs.msg import JointJog


class JointSubscriber(Node):
	def __init__(self):
		super().__init__('js_subscriber')
		self.subscription = self.create_subscription(
			JointJog, 
			"/servo_server/delta_joint_cmds", 
			self.listen_joints,
			10
		)
		self.subscription
	
	def listen_joints(self, msg):
		for i in range(len(msg.joint_names)):
			self.get_logger().info(
				'joint: %s, vel: %f' % (msg.joint_names[i], msg.velocities[i])
			)

def main(args=None):
	rclpy.init(args=args)
	node = JointSubscriber()
	rclpy.spin(node)
	node.destroy_node()
	rclpy.shutdown()


if __name__ == "__main__":
	main()
