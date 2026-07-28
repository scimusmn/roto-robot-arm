import rclpy
from rclpy.node import Node
from control_msgs.msg import JointJog
from xarm_msgs.MoveVelocity.srv import MoveVelocity


class JsMoveClient(Node):
	def __init__(self):
		super().__init__('js_move_client')
		self.cli = self.create_client(MoveVelocity, '/xarm_api/vc_set_joint_velocity')
		self.publisher = self.create_publisher(JointJog, "/servo_server/delta_joint_cmds", 10)
		self.timer = self.create_timer(0.5, self.publish_ax1)
	

	def publish_ax1(self):
		self.get_logger().info("publishing to joint 1")
		self.publish([ ('joint1', 1) ])
	

	def publish(self, axis_vels):
		msg = JointJog()
		for vel in axis_vels:
			msg.joint_names.append(vel[0])
			msg.velocities.append(vel[1])
		msg.header.frame_id = 'joint'
		msg.header.stamp = self.get_clock().now().to_msg()
		self.publisher.publish(msg)


def main(args=None):
	rclpy.init(args=args)
	node = JsMoveClient()
	rclpy.spin(node)
	node.destroy_node()
	rclpy.shutdown()


if __name__ == "__main__":
	main()
