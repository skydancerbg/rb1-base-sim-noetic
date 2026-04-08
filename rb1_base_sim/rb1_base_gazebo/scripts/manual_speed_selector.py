#!/usr/bin/env python3

import rospy
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy


class ManualSpeedSelector(object):
    def __init__(self):
        self._normal_multiplier = rospy.get_param("~normal_multiplier", 1.0)
        self._turbo_multiplier = rospy.get_param("~turbo_multiplier", 1.6)
        self._mode_axis_turbo = rospy.get_param("~mode_axis_turbo", 7)
        self._mode_axis_normal = rospy.get_param("~mode_axis_normal", 7)
        self._mode_axis_threshold = rospy.get_param("~mode_axis_threshold", 0.5)
        self._enable_button = rospy.get_param("~enable_button", 5)
        self._left_linear_axis = rospy.get_param("~left_linear_axis", 1)
        self._left_angular_axis = rospy.get_param("~left_angular_axis", 0)
        self._left_linear_scale = rospy.get_param("~left_linear_scale", -0.35)
        self._left_angular_scale = rospy.get_param("~left_angular_scale", -0.8)
        self._mode = "NORMAL"
        self._left_cmd = Twist()
        self._raw_cmd = Twist()

        joy_topic = rospy.get_param("~joy_topic", "joy")
        input_cmd_vel_topic = rospy.get_param("~input_cmd_vel_topic", "pad_teleop/cmd_vel_raw")
        output_cmd_vel_topic = rospy.get_param("~output_cmd_vel_topic", "pad_teleop/cmd_vel")

        self._cmd_pub = rospy.Publisher(output_cmd_vel_topic, Twist, queue_size=10)
        rospy.Subscriber(joy_topic, Joy, self._joy_cb, queue_size=10)
        rospy.Subscriber(input_cmd_vel_topic, Twist, self._cmd_cb, queue_size=10)

        rospy.loginfo("manual speed mode: %s", self._mode)

    def _set_mode(self, mode):
        if self._mode == mode:
            return
        self._mode = mode
        rospy.loginfo("manual speed mode: %s", self._mode)

    def _axis_value(self, axes, idx):
        if idx < 0 or idx >= len(axes):
            return 0.0
        return axes[idx]

    def _button_pressed(self, buttons, idx):
        if idx < 0 or idx >= len(buttons):
            return False
        return buttons[idx] != 0

    def _merge_axis(self, raw_value, left_value):
        return raw_value if abs(raw_value) >= abs(left_value) else left_value

    def _publish_cmd(self):
        multiplier = self._normal_multiplier if self._mode == "NORMAL" else self._turbo_multiplier

        out = Twist()
        out.linear.x = self._merge_axis(self._raw_cmd.linear.x, self._left_cmd.linear.x) * multiplier
        out.angular.z = self._merge_axis(self._raw_cmd.angular.z, self._left_cmd.angular.z) * multiplier
        self._cmd_pub.publish(out)

    def _joy_cb(self, msg):
        turbo_value = self._axis_value(msg.axes, self._mode_axis_turbo)
        normal_value = self._axis_value(msg.axes, self._mode_axis_normal)

        if turbo_value <= -self._mode_axis_threshold:
            self._set_mode("TURBO")
        elif normal_value >= self._mode_axis_threshold:
            self._set_mode("NORMAL")

        if self._button_pressed(msg.buttons, self._enable_button):
            self._left_cmd.linear.x = self._axis_value(msg.axes, self._left_linear_axis) * self._left_linear_scale
            self._left_cmd.angular.z = self._axis_value(msg.axes, self._left_angular_axis) * self._left_angular_scale
        else:
            self._left_cmd = Twist()

        self._publish_cmd()

    def _cmd_cb(self, msg):
        self._raw_cmd = msg
        self._publish_cmd()


if __name__ == "__main__":
    rospy.init_node("manual_speed_selector")
    ManualSpeedSelector()
    rospy.spin()
