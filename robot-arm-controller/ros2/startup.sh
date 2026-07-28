#!/usr/bin/env bash
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch xarm_api uf850_driver.launch.py robot_ip:=192.168.1.210 &
ros2 run js_control polar_serial
