#!/usr/bin/env python3

import math
import os
import subprocess
import sys
import time

import rospy
from geometry_msgs.msg import Twist
from nav_msgs.msg import OccupancyGrid, Odometry
from sensor_msgs.msg import LaserScan
from tf.transformations import euler_from_quaternion


def normalize_angle(angle):
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


class NeoWorkshopAutoMap(object):
    def __init__(self):
        rospy.init_node("neo_workshop_auto_map", anonymous=False)

        self.cmd_topic = "/robot/robotnik_base_control/cmd_vel"
        self.scan_topic = "/robot/front_laser/scan"
        self.odom_topic = "/robot/robotnik_base_control/odom"
        self.map_topic = "/robot/map"

        self.cmd_pub = rospy.Publisher(self.cmd_topic, Twist, queue_size=1)
        self.scan_msg = None
        self.current_yaw = None
        self.current_x = None
        self.current_y = None

        self.stop_clearance = 0.60
        self.resume_clearance = 0.90
        self.rotate_speed = 0.24
        self.startup_scan_speed = 0.30
        self.turn_speed = 0.34
        self.forward_speed = 0.16
        self.max_heading_correction = 0.18
        self.reverse_speed = -0.08
        self.escape_clearance = 0.75
        self.status_log_interval = 2.0
        self.progress_window = 8.0
        self.min_progress_distance = 0.10
        self.recovery_count = 0
        self.startup_breakout_distance = 0.90
        self.startup_breakout_heading = None
        self.startup_best_scan_angle_deg = None

        # Route chosen from the actual neo_workshop.world geometry:
        # upper room -> left corridor -> lower room -> right side -> center return.
        self.route = [
            {"name": "upper_entry", "kind": "waypoint", "x": 2.05, "y": 0.15},
            {"name": "upper_right", "kind": "waypoint", "x": 4.25, "y": 2.45, "scan": True},
            {"name": "upper_center", "kind": "waypoint", "x": 1.55, "y": 2.95},
            {"name": "upper_left", "kind": "waypoint", "x": -3.20, "y": 2.95, "scan": True},
            {"name": "left_mid", "kind": "waypoint", "x": -4.85, "y": 1.40},
            {"name": "left_lower", "kind": "waypoint", "x": -4.85, "y": -2.00, "scan": True},
            {"name": "bottom_left", "kind": "waypoint", "x": -4.85, "y": -5.85},
            {"name": "bottom_center", "kind": "waypoint", "x": -1.20, "y": -5.85, "scan": True},
            {"name": "bottom_right", "kind": "waypoint", "x": 2.10, "y": -5.55},
            {"name": "right_lower", "kind": "waypoint", "x": 4.05, "y": -3.30, "scan": True},
            {"name": "center_right", "kind": "waypoint", "x": 2.10, "y": -1.85},
            {"name": "center_mid", "kind": "waypoint", "x": 0.20, "y": -1.80, "scan": True},
            {"name": "center_north", "kind": "waypoint", "x": 0.20, "y": 0.15},
            {"name": "final_scan", "kind": "scan"},
        ]

        rospy.Subscriber(self.scan_topic, LaserScan, self.scan_callback, queue_size=1)
        rospy.Subscriber(self.odom_topic, Odometry, self.odom_callback, queue_size=1)
        rospy.on_shutdown(self.on_shutdown)

    def scan_callback(self, msg):
        self.scan_msg = msg

    def odom_callback(self, msg):
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y
        orientation = msg.pose.pose.orientation
        quaternion = [orientation.x, orientation.y, orientation.z, orientation.w]
        _, _, self.current_yaw = euler_from_quaternion(quaternion)

    def wait_for_sim_time(self):
        rospy.loginfo("Waiting for simulation time to start")
        rate = rospy.Rate(10)
        while not rospy.is_shutdown() and rospy.Time.now().to_sec() == 0.0:
            rate.sleep()
        rospy.loginfo("Simulation time active at %.3f", rospy.Time.now().to_sec())

    def wait_for_connections(self):
        rospy.loginfo("Waiting for cmd_vel subscriber on %s", self.cmd_topic)
        rate = rospy.Rate(10)
        while not rospy.is_shutdown() and self.cmd_pub.get_num_connections() == 0:
            rate.sleep()
        rospy.loginfo("cmd_vel subscriber detected")

    def wait_for_topics(self):
        rospy.loginfo("Waiting for laser and odometry topics")
        rospy.wait_for_message(self.scan_topic, LaserScan, timeout=30.0)
        rospy.wait_for_message(self.odom_topic, Odometry, timeout=30.0)
        rospy.loginfo("Required topics received")

    def publish_twist(self, linear=0.0, angular=0.0):
        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        self.cmd_pub.publish(twist)

    def stop_robot(self):
        twist = Twist()
        for _ in range(5):
            self.cmd_pub.publish(twist)
            time.sleep(0.05)

    def on_shutdown(self):
        rospy.loginfo("Shutdown requested, stopping robot safely")
        self.stop_robot()

    def clearance_window(self, center_ratio, width_ratio):
        if self.scan_msg is None or not self.scan_msg.ranges:
            return float("inf")

        total = len(self.scan_msg.ranges)
        center = int(total * center_ratio)
        half_window = max(6, int(total * width_ratio * 0.5))
        start = max(0, center - half_window)
        stop = min(total, center + half_window)

        distances = []
        for idx in range(start, stop):
            distance = self.scan_msg.ranges[idx]
            if math.isfinite(distance):
                distances.append(distance)

        return min(distances) if distances else float("inf")

    def front_clearance(self):
        return self.clearance_window(0.5, 0.08)

    def left_clearance(self):
        return self.clearance_window(0.72, 0.18)

    def right_clearance(self):
        return self.clearance_window(0.28, 0.18)

    def settle(self, duration):
        end_time = rospy.Time.now() + rospy.Duration.from_sec(duration)
        rate = rospy.Rate(10)
        while not rospy.is_shutdown() and rospy.Time.now() < end_time:
            self.publish_twist(0.0, 0.0)
            rate.sleep()

    def current_pose_tuple(self):
        return self.current_x, self.current_y, self.current_yaw

    def clearance_summary(self):
        return self.front_clearance(), self.left_clearance(), self.right_clearance()

    def drive_for_duration(self, linear, angular, duration):
        end_time = rospy.Time.now() + rospy.Duration.from_sec(duration)
        rate = rospy.Rate(10)
        while not rospy.is_shutdown() and rospy.Time.now() < end_time:
            self.publish_twist(linear, angular)
            rate.sleep()
        self.stop_robot()

    def breakout_reverse(self, duration, label):
        if self.current_x is None or self.current_y is None:
            rospy.logwarn("%s started without odometry pose, using timed reverse only", label)
            self.drive_for_duration(self.reverse_speed, 0.0, duration)
            return True

        target_distance = abs(self.reverse_speed) * duration
        start_x = self.current_x
        start_y = self.current_y
        start_time = rospy.Time.now()
        last_log_time = 0.0
        rospy.loginfo("%s started: target reverse distance %.2f m", label, target_distance)

        rate = rospy.Rate(10)
        while not rospy.is_shutdown() and rospy.Time.now() < start_time + rospy.Duration.from_sec(duration):
            traveled = math.hypot(self.current_x - start_x, self.current_y - start_y)
            now_sec = rospy.Time.now().to_sec()
            if now_sec - last_log_time >= 0.5:
                rospy.loginfo("%s progress: traveled %.2f / %.2f m", label, traveled, target_distance)
                last_log_time = now_sec
            self.publish_twist(self.reverse_speed, 0.0)
            rate.sleep()

        self.stop_robot()
        traveled = math.hypot(self.current_x - start_x, self.current_y - start_y)
        if traveled < max(0.03, 0.4 * target_distance):
            rospy.logwarn("%s blocked or interrupted: traveled only %.2f / %.2f m", label, traveled, target_distance)
            return False

        rospy.loginfo("%s completed: traveled %.2f / %.2f m", label, traveled, target_distance)
        return True

    def breakout_forward_along_heading(self, target_distance, label):
        if self.current_x is None or self.current_y is None or self.current_yaw is None:
            rospy.logerr("%s failed: odometry pose is not available", label)
            return False

        start_x = self.current_x
        start_y = self.current_y
        start_time = rospy.Time.now()
        deadline = start_time + rospy.Duration.from_sec(max(8.0, 14.0 * target_distance))
        last_log_time = 0.0
        rate = rospy.Rate(10)
        rospy.loginfo(
            "%s started: target distance %.2f m at heading %.2f rad from pose (%.2f, %.2f, %.2f)",
            label,
            target_distance,
            self.startup_breakout_heading,
            self.current_x,
            self.current_y,
            self.current_yaw,
        )

        while not rospy.is_shutdown():
            if rospy.Time.now() > deadline:
                traveled = math.hypot(self.current_x - start_x, self.current_y - start_y)
                rospy.logwarn(
                    "%s failed: timeout after %.1f s, traveled %.2f / %.2f m",
                    label,
                    (rospy.Time.now() - start_time).to_sec(),
                    traveled,
                    target_distance,
                )
                self.stop_robot()
                return False

            traveled = math.hypot(self.current_x - start_x, self.current_y - start_y)
            if traveled >= target_distance:
                self.stop_robot()
                rospy.loginfo(
                    "%s completed: traveled %.2f / %.2f m, end pose=(%.2f, %.2f, %.2f)",
                    label,
                    traveled,
                    target_distance,
                    self.current_x,
                    self.current_y,
                    self.current_yaw,
                )
                return True

            front, left, right = self.clearance_summary()
            heading_error = normalize_angle(self.startup_breakout_heading - self.current_yaw)
            if front < self.stop_clearance:
                rospy.logwarn(
                    "%s blocked or interrupted: front=%.2f m left=%.2f m right=%.2f m traveled=%.2f / %.2f m",
                    label,
                    front,
                    left,
                    right,
                    traveled,
                    target_distance,
                )
                self.stop_robot()
                return False

            now_sec = rospy.Time.now().to_sec()
            if now_sec - last_log_time >= 0.75:
                rospy.loginfo(
                    "%s progress: traveled %.2f / %.2f m pose=(%.2f, %.2f, %.2f) heading_error=%.2f rad front=%.2f m",
                    label,
                    traveled,
                    target_distance,
                    self.current_x,
                    self.current_y,
                    self.current_yaw,
                    heading_error,
                    front,
                )
                last_log_time = now_sec

            angular = max(-self.max_heading_correction, min(self.max_heading_correction, 0.8 * heading_error))
            self.publish_twist(self.forward_speed, angular)
            rate.sleep()

        self.stop_robot()
        return False

    def rotate_by(self, angle, speed):
        if self.current_yaw is None:
            raise rospy.ROSException("Odometry is not available for rotation")

        target = abs(angle)
        direction = 1.0 if angle >= 0.0 else -1.0
        accumulated = 0.0
        last_yaw = self.current_yaw
        rate = rospy.Rate(10)

        while not rospy.is_shutdown():
            accumulated += abs(normalize_angle(self.current_yaw - last_yaw))
            last_yaw = self.current_yaw

            if accumulated >= max(0.0, target - 0.04):
                break

            self.publish_twist(0.0, direction * abs(speed))
            rate.sleep()

        self.stop_robot()

    def rotate_towards(self, target_heading, tolerance=0.08):
        rate = rospy.Rate(10)
        last_log_time = 0.0
        while not rospy.is_shutdown():
            heading_error = normalize_angle(target_heading - self.current_yaw)
            if abs(heading_error) <= tolerance:
                break

            now_sec = rospy.Time.now().to_sec()
            if now_sec - last_log_time >= self.status_log_interval:
                rospy.loginfo(
                    "Aligning yaw: current=%.2f rad target=%.2f rad error=%.2f rad",
                    self.current_yaw,
                    target_heading,
                    heading_error,
                )
                last_log_time = now_sec

            angular = max(-self.rotate_speed, min(self.rotate_speed, 0.9 * heading_error))
            self.publish_twist(0.0, angular)
            rate.sleep()

        self.stop_robot()

    def scan_in_place(self):
        rospy.loginfo("Performing deliberate scan rotation")
        self.rotate_by(2.0 * math.pi, 0.22)
        self.settle(1.0)

    def find_best_opening_heading(self):
        rospy.loginfo("Performing startup 360-degree scan to find the clearest heading")
        start_front, start_left, start_right = self.clearance_summary()
        start_yaw = self.current_yaw
        rospy.loginfo(
            "Startup scan started: yaw=%.2f rad front=%.2f m left=%.2f m right=%.2f m",
            self.current_yaw,
            start_front,
            start_left,
            start_right,
        )
        best_heading = self.current_yaw
        best_clearance = self.front_clearance()
        best_scan_angle_deg = 0
        accumulated = 0.0
        last_yaw = self.current_yaw
        sample_step_deg = 10
        next_sample_deg = 0
        sampled_summary = []
        rate = rospy.Rate(10)

        while not rospy.is_shutdown():
            current_clearance = self.front_clearance()
            if current_clearance > best_clearance:
                best_clearance = current_clearance
                best_heading = self.current_yaw
                best_scan_angle_deg = int(round(math.degrees(accumulated))) % 360
                rospy.loginfo(
                    "Startup scan update: new best heading %.2f rad at scan angle %d deg with front clearance %.2f m",
                    best_heading,
                    best_scan_angle_deg,
                    best_clearance,
                )

            while next_sample_deg <= 360 and math.degrees(accumulated) >= next_sample_deg:
                sampled_summary.append(
                    {
                        "scan_deg": next_sample_deg % 360,
                        "yaw": self.current_yaw,
                        "distance": current_clearance,
                    }
                )
                next_sample_deg += sample_step_deg

            accumulated += abs(normalize_angle(self.current_yaw - last_yaw))
            last_yaw = self.current_yaw

            if accumulated >= 2.0 * math.pi - 0.08:
                break

            self.publish_twist(0.0, self.startup_scan_speed)
            rate.sleep()

        self.stop_robot()
        if not sampled_summary or sampled_summary[-1]["scan_deg"] != 350:
            sampled_summary.append(
                {
                    "scan_deg": 350,
                    "yaw": self.current_yaw,
                    "distance": self.front_clearance(),
                }
            )
        end_front, end_left, end_right = self.clearance_summary()
        summary_lines = []
        chunk = []
        for sample in sampled_summary:
            chunk.append(
                "%3ddeg: %.2fm" % (sample["scan_deg"], sample["distance"])
            )
            if len(chunk) == 6:
                summary_lines.append(" | ".join(chunk))
                chunk = []
        if chunk:
            summary_lines.append(" | ".join(chunk))

        rospy.loginfo(
            "Startup scan completed: yaw=%.2f rad front=%.2f m left=%.2f m right=%.2f m",
            self.current_yaw,
            end_front,
            end_left,
            end_right,
        )
        rospy.loginfo("Startup scan 10-degree summary:\n%s", "\n".join(summary_lines))
        rospy.loginfo(
            "Best opening heading found: scan_angle=%d deg heading=%.2f rad clearance=%.2f m",
            best_scan_angle_deg,
            best_heading,
            best_clearance,
        )
        rospy.loginfo(
            "Startup scan frame summary: start_yaw=%.2f rad end_yaw=%.2f rad target_heading=%.2f rad",
            start_yaw,
            self.current_yaw,
            best_heading,
        )
        self.startup_best_scan_angle_deg = best_scan_angle_deg
        return best_heading, best_clearance

    def startup_escape_and_align(self):
        initial_front = self.front_clearance()
        initial_left = self.left_clearance()
        initial_right = self.right_clearance()
        rospy.loginfo(
            "Startup alignment phase: yaw=%.2f rad front=%.2f m left=%.2f m right=%.2f m",
            self.current_yaw,
            initial_front,
            initial_left,
            initial_right,
        )

        if initial_front < self.escape_clearance:
            rospy.logwarn("Startup pose is tight, backing up slightly before heading search")
            self.breakout_reverse(0.9, "Startup breakout")
            self.settle(0.5)

        best_heading, best_clearance = self.find_best_opening_heading()
        yaw_before_alignment = self.current_yaw
        heading_error = normalize_angle(best_heading - self.current_yaw)
        rospy.loginfo(
            "Startup alignment target selected: best_scan_angle=%d deg current_yaw=%.2f rad target_yaw=%.2f rad yaw_error=%.2f rad best_clearance=%.2f m",
            self.startup_best_scan_angle_deg,
            self.current_yaw,
            best_heading,
            heading_error,
            best_clearance,
        )
        self.rotate_towards(best_heading, tolerance=0.10)
        rospy.loginfo(
            "Startup alignment result: current_yaw_before=%.2f rad target_yaw=%.2f rad final_yaw=%.2f rad final_error=%.2f rad",
            yaw_before_alignment,
            best_heading,
            self.current_yaw,
            normalize_angle(best_heading - self.current_yaw),
        )

        if best_clearance < self.escape_clearance:
            rospy.logwarn(
                "Best startup opening is still narrow (%.2f m), backing up again and re-aligning",
                best_clearance,
            )
            self.breakout_reverse(0.8, "Startup breakout retry")
            self.settle(0.5)
            best_heading, _ = self.find_best_opening_heading()
            yaw_before_alignment = self.current_yaw
            heading_error = normalize_angle(best_heading - self.current_yaw)
            rospy.loginfo(
                "Retry alignment target selected: best_scan_angle=%d deg current_yaw=%.2f rad target_yaw=%.2f rad yaw_error=%.2f rad",
                self.startup_best_scan_angle_deg,
                self.current_yaw,
                best_heading,
                heading_error,
            )
            self.rotate_towards(best_heading, tolerance=0.10)
            rospy.loginfo(
                "Retry alignment result: current_yaw_before=%.2f rad target_yaw=%.2f rad final_yaw=%.2f rad final_error=%.2f rad",
                yaw_before_alignment,
                best_heading,
                self.current_yaw,
                normalize_angle(best_heading - self.current_yaw),
            )

        final_front, final_left, final_right = self.clearance_summary()
        self.startup_breakout_heading = best_heading
        rospy.loginfo(
            "Startup alignment completed: yaw=%.2f rad front=%.2f m left=%.2f m right=%.2f m",
            self.current_yaw,
            final_front,
            final_left,
            final_right,
        )
        self.settle(0.8)
        breakout_ok = self.breakout_forward_along_heading(self.startup_breakout_distance, "Startup breakout forward")
        self.settle(0.5)
        return breakout_ok

    def maybe_stop_mapping_stack(self):
        if os.environ.get("NEO_WORKSHOP_STOP_AFTER_SAVE", "0") != "1":
            return

        repo_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        stop_script = os.path.join(repo_root, "tools", "kill_gazebo_ros.sh")

        if not os.path.isfile(stop_script):
            rospy.logwarn("Requested automatic stop, but helper script is missing: %s", stop_script)
            return

        rospy.loginfo("Successful mapping run complete, stopping mapping stack via %s", stop_script)
        subprocess.run([stop_script], check=False)

    def obstacle_recovery_turn(self, desired_heading):
        self.recovery_count += 1
        front = self.front_clearance()
        left = self.left_clearance()
        right = self.right_clearance()
        turn_direction = 1.0 if self.left_clearance() >= self.right_clearance() else -1.0
        reason = "left clearance is greater or equal" if turn_direction > 0.0 else "right clearance is greater"
        rospy.logwarn(
            "Obstacle recovery #%d: front=%.2f m left=%.2f m right=%.2f m, turning %s because %s",
            self.recovery_count,
            front,
            left,
            right,
            "left" if turn_direction > 0.0 else "right",
            reason,
        )
        if self.recovery_count >= 3:
            rospy.logwarn("Repeated recovery detected: recovery count is now %d", self.recovery_count)

        reversed_first = False
        if front < 0.45:
            rospy.logwarn("Front clearance is critically low, backing up briefly before turning")
            reversed_first = True
            self.breakout_reverse(0.8, "Recovery reverse")
            self.settle(0.3)

        recovery_start = rospy.Time.now()
        end_time = rospy.Time.now() + rospy.Duration.from_sec(9.0)
        rate = rospy.Rate(10)
        last_log_time = 0.0
        while not rospy.is_shutdown() and rospy.Time.now() < end_time:
            if self.front_clearance() >= self.resume_clearance:
                break
            now_sec = rospy.Time.now().to_sec()
            if now_sec - last_log_time >= 1.0:
                front, left, right = self.clearance_summary()
                rospy.loginfo(
                    "Recovery in progress: elapsed=%.1f s front=%.2f m left=%.2f m right=%.2f m reverse_first=%s",
                    (rospy.Time.now() - recovery_start).to_sec(),
                    front,
                    left,
                    right,
                    reversed_first,
                )
                last_log_time = now_sec
            self.publish_twist(0.0, turn_direction * self.turn_speed)
            rate.sleep()

        self.stop_robot()
        recovery_elapsed = (rospy.Time.now() - recovery_start).to_sec()
        front, left, right = self.clearance_summary()
        rospy.loginfo(
            "Recovery finished: elapsed=%.1f s front=%.2f m left=%.2f m right=%.2f m",
            recovery_elapsed,
            front,
            left,
            right,
        )
        if self.front_clearance() >= self.stop_clearance:
            self.rotate_towards(desired_heading, tolerance=0.18)
            self.recovery_count = 0
        else:
            rospy.logwarn("Recovery ended without sufficient front clearance to re-align to the waypoint heading")

    def drive_to_waypoint(self, waypoint):
        target_x = waypoint["x"]
        target_y = waypoint["y"]
        timeout = max(70.0, 24.0 * math.hypot(target_x - self.current_x, target_y - self.current_y))
        deadline = rospy.Time.now() + rospy.Duration.from_sec(timeout)
        rate = rospy.Rate(10)
        start_time = rospy.Time.now()
        last_status_log = 0.0
        progress_reference_time = rospy.Time.now()
        progress_reference_distance = math.hypot(target_x - self.current_x, target_y - self.current_y)
        progress_reference_pose = (self.current_x, self.current_y)
        last_controller_mode = None

        rospy.loginfo(
            "Driving to waypoint %s at (%.2f, %.2f)",
            waypoint["name"],
            target_x,
            target_y,
        )

        while not rospy.is_shutdown():
            if rospy.Time.now() > deadline:
                rospy.logerr("Timed out before reaching waypoint %s", waypoint["name"])
                return False

            dx = target_x - self.current_x
            dy = target_y - self.current_y
            distance = math.hypot(dx, dy)
            if distance <= 0.22:
                elapsed = (rospy.Time.now() - start_time).to_sec()
                self.stop_robot()
                rospy.loginfo(
                    "Waypoint %s reached: pose=(%.2f, %.2f, %.2f) elapsed=%.1f s",
                    waypoint["name"],
                    self.current_x,
                    self.current_y,
                    self.current_yaw,
                    elapsed,
                )
                return True

            desired_heading = math.atan2(dy, dx)
            heading_error = normalize_angle(desired_heading - self.current_yaw)
            timeout_remaining = (deadline - rospy.Time.now()).to_sec()
            now_sec = rospy.Time.now().to_sec()
            controller_mode = "forward"

            if self.front_clearance() < self.stop_clearance and abs(heading_error) < 0.45:
                controller_mode = "recovery"
                rospy.logwarn(
                    "Waypoint %s entering recovery: pose=(%.2f, %.2f, %.2f) distance=%.2f m heading_error=%.2f rad timeout_remaining=%.1f s",
                    waypoint["name"],
                    self.current_x,
                    self.current_y,
                    self.current_yaw,
                    distance,
                    heading_error,
                    timeout_remaining,
                )
                self.obstacle_recovery_turn(desired_heading)
                rate.sleep()
                continue

            if abs(heading_error) > 0.35:
                controller_mode = "rotate"
                angular = max(-self.rotate_speed, min(self.rotate_speed, 0.9 * heading_error))
                self.publish_twist(0.0, angular)
            else:
                linear = min(self.forward_speed, max(0.08, 0.55 * distance))
                angular = max(
                    -self.max_heading_correction,
                    min(self.max_heading_correction, 0.7 * heading_error),
                )
                self.publish_twist(linear, angular)

            if controller_mode != last_controller_mode:
                rospy.loginfo(
                    "Waypoint %s controller mode -> %s",
                    waypoint["name"],
                    controller_mode,
                )
                last_controller_mode = controller_mode

            if now_sec - last_status_log >= self.status_log_interval:
                rospy.loginfo(
                    "Waypoint %s status: target=(%.2f, %.2f) pose=(%.2f, %.2f, %.2f) distance=%.2f m heading_error=%.2f rad mode=%s timeout_remaining=%.1f s elapsed=%.1f s",
                    waypoint["name"],
                    target_x,
                    target_y,
                    self.current_x,
                    self.current_y,
                    self.current_yaw,
                    distance,
                    heading_error,
                    controller_mode,
                    timeout_remaining,
                    (rospy.Time.now() - start_time).to_sec(),
                )
                last_status_log = now_sec

            if (rospy.Time.now() - progress_reference_time).to_sec() >= self.progress_window:
                moved = math.hypot(
                    self.current_x - progress_reference_pose[0],
                    self.current_y - progress_reference_pose[1],
                )
                progress_gain = progress_reference_distance - distance
                if progress_gain < self.min_progress_distance:
                    rospy.logwarn(
                        "No-progress warning at waypoint %s: progress_gain=%.2f m moved=%.2f m over %.1f s",
                        waypoint["name"],
                        progress_gain,
                        moved,
                        self.progress_window,
                    )
                if moved < 0.05 and distance > 0.40:
                    rospy.logwarn(
                        "Stuck detection at waypoint %s: pose hardly changed (%.2f m) over %.1f s while distance is %.2f m",
                        waypoint["name"],
                        moved,
                        self.progress_window,
                        distance,
                    )
                progress_reference_time = rospy.Time.now()
                progress_reference_distance = distance
                progress_reference_pose = (self.current_x, self.current_y)

            rate.sleep()

        return False

    def save_map(self):
        rospy.loginfo("Waiting for map topic before saving")
        rospy.wait_for_message(self.map_topic, OccupancyGrid, timeout=30.0)

        localization_root = subprocess.check_output(
            ["rospack", "find", "rb1_base_localization"], text=True
        ).strip()
        map_dir = os.path.join(localization_root, "maps", "neo_workshop")
        os.makedirs(map_dir, exist_ok=True)

        final_prefix = os.path.join(map_dir, "neo_workshop")
        temp_prefix = os.path.join(map_dir, "neo_workshop_tmp")
        temp_yaml = temp_prefix + ".yaml"
        temp_pgm = temp_prefix + ".pgm"
        final_yaml = final_prefix + ".yaml"
        final_pgm = final_prefix + ".pgm"

        for temp_file in (temp_yaml, temp_pgm):
            if os.path.exists(temp_file):
                os.remove(temp_file)

        rospy.loginfo("Saving map to temporary basename %s", temp_prefix)
        command = [
            "rosrun",
            "map_server",
            "map_saver",
            "-f",
            temp_prefix,
            "map:=/robot/map",
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            rospy.logerr("map_saver failed with return code %s", result.returncode)
            if result.stdout:
                rospy.logerr("map_saver stdout:\n%s", result.stdout.strip())
            if result.stderr:
                rospy.logerr("map_saver stderr:\n%s", result.stderr.strip())
            return False

        if not (os.path.isfile(temp_yaml) and os.path.isfile(temp_pgm)):
            rospy.logerr("Temporary map files were not produced completely")
            return False

        if os.path.getsize(temp_yaml) == 0 or os.path.getsize(temp_pgm) == 0:
            rospy.logerr("Temporary map files are empty, refusing to replace the active map")
            return False

        os.replace(temp_yaml, final_yaml)
        os.replace(temp_pgm, final_pgm)
        rospy.loginfo("Map save promoted to active files %s.[yaml|pgm]", final_prefix)
        return True

    def run(self):
        self.wait_for_sim_time()
        self.wait_for_topics()
        self.wait_for_connections()
        self.settle(2.0)
        if not self.startup_escape_and_align():
            rospy.logerr("Aborting route because startup breakout failed")
            return False

        first_waypoint = self.route[0]
        first_heading = math.atan2(first_waypoint["y"] - self.current_y, first_waypoint["x"] - self.current_x)
        heading_conflict = abs(normalize_angle(first_heading - self.startup_breakout_heading))
        rospy.loginfo(
            "Pre-route handoff: current_pose=(%.2f, %.2f, %.2f) first_waypoint=(%.2f, %.2f) heading_to_first_waypoint=%.2f rad breakout_heading=%.2f rad heading_conflict=%.2f rad",
            self.current_x,
            self.current_y,
            self.current_yaw,
            first_waypoint["x"],
            first_waypoint["y"],
            first_heading,
            self.startup_breakout_heading,
            heading_conflict,
        )
        if heading_conflict > 0.9:
            rospy.logwarn(
                "First waypoint heading differs strongly from breakout heading (%.2f rad). Breakout phase has already been completed before waypoint pursuit.",
                heading_conflict,
            )

        for step in self.route:
            if rospy.is_shutdown():
                rospy.logwarn("Route aborted because ROS shutdown was requested")
                return False

            if not self.drive_to_waypoint(step):
                rospy.logerr("Aborting route after failing waypoint %s", step["name"])
                return False

            self.settle(0.8)
            if step.get("scan", False):
                self.scan_in_place()

        self.scan_in_place()
        rospy.loginfo("Route complete, saving map")
        if self.save_map():
            rospy.loginfo("neo_workshop mapping workflow completed")
            self.maybe_stop_mapping_stack()
            return True
        else:
            rospy.logerr("neo_workshop mapping workflow finished with map save errors")
            return False


if __name__ == "__main__":
    try:
        sys.exit(0 if NeoWorkshopAutoMap().run() else 1)
    except rospy.ROSInterruptException:
        pass
    except subprocess.TimeoutExpired:
        rospy.logerr("Timed out while saving the map")
    except subprocess.CalledProcessError as exc:
        rospy.logerr("Failed to resolve required ROS package path: %s", exc)
