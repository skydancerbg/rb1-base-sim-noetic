#!/usr/bin/env python3

import math

import rospy
from actionlib_msgs.msg import GoalID
from move_base_msgs.msg import MoveBaseActionGoal, RecoveryStatus


class FrontierGoalGuard(object):
    def __init__(self):
        self.blacklist_radius = rospy.get_param("~blacklist_radius", 1.0)
        self.blacklist_duration = rospy.get_param("~blacklist_duration", 60.0)
        self.recovery_cancel_cooldown = rospy.get_param("~recovery_cancel_cooldown", 2.0)

        self.blacklist = []
        self.current_goal_id = None
        self.current_goal_xy = None
        self.current_goal_blacklisted = False
        self.current_goal_recovery_count = 0
        self.last_cancel_time = rospy.Time(0)

        self.cancel_pub = rospy.Publisher("move_base/cancel", GoalID, queue_size=10)
        rospy.Subscriber("move_base/goal", MoveBaseActionGoal, self.goal_callback, queue_size=10)
        rospy.Subscriber("move_base/recovery_status", RecoveryStatus, self.recovery_callback, queue_size=10)

    def purge_blacklist(self):
        now = rospy.Time.now()
        self.blacklist = [entry for entry in self.blacklist if entry["expires"] > now]

    def is_explore_goal(self, goal_id):
        return goal_id.startswith("/robot/explore-")

    def distance(self, point_a, point_b):
        return math.hypot(point_a[0] - point_b[0], point_a[1] - point_b[1])

    def blacklist_match(self, goal_xy):
        self.purge_blacklist()
        for entry in self.blacklist:
            if self.distance(goal_xy, entry["xy"]) <= self.blacklist_radius:
                return entry
        return None

    def cancel_goal(self, goal_id, reason):
        now = rospy.Time.now()
        if (now - self.last_cancel_time).to_sec() < self.recovery_cancel_cooldown:
            return

        self.cancel_pub.publish(GoalID(id=goal_id))
        self.last_cancel_time = now
        rospy.logwarn("Frontier goal guard canceled goal %s: %s", goal_id, reason)

    def goal_callback(self, msg):
        goal_id = msg.goal_id.id
        goal_xy = (
            msg.goal.target_pose.pose.position.x,
            msg.goal.target_pose.pose.position.y,
        )

        if not self.is_explore_goal(goal_id):
            return

        entry = self.blacklist_match(goal_xy)
        if entry is not None:
            reason = (
                "goal at (%.2f, %.2f) is within %.2f m of blacklisted frontier region "
                "centered at (%.2f, %.2f)"
            ) % (
                goal_xy[0],
                goal_xy[1],
                self.blacklist_radius,
                entry["xy"][0],
                entry["xy"][1],
            )
            self.cancel_goal(goal_id, reason)
            return

        self.current_goal_id = goal_id
        self.current_goal_xy = goal_xy
        self.current_goal_blacklisted = False
        self.current_goal_recovery_count = 0
        rospy.loginfo(
            "Frontier goal guard tracking explore goal %s at (%.2f, %.2f)",
            goal_id,
            goal_xy[0],
            goal_xy[1],
        )

    def recovery_callback(self, msg):
        if self.current_goal_id is None or self.current_goal_xy is None:
            return
        if not self.is_explore_goal(self.current_goal_id):
            return
        if self.current_goal_blacklisted:
            return

        self.current_goal_recovery_count += 1
        if self.current_goal_recovery_count < 2:
            rospy.loginfo(
                "Frontier goal guard observed first recovery for goal %s at (%.2f, %.2f); "
                "waiting for a repeated recovery before blacklisting",
                self.current_goal_id,
                self.current_goal_xy[0],
                self.current_goal_xy[1],
            )
            return

        now = rospy.Time.now()
        self.blacklist.append(
            {
                "xy": self.current_goal_xy,
                "expires": now + rospy.Duration.from_sec(self.blacklist_duration),
            }
        )
        rospy.logwarn(
            "Frontier goal guard blacklisted frontier region around (%.2f, %.2f) for %.1f s "
            "after recovery behavior %s",
            self.current_goal_xy[0],
            self.current_goal_xy[1],
            self.blacklist_duration,
            msg.recovery_behavior_name,
        )
        self.cancel_goal(
            self.current_goal_id,
            "recovery behavior %s triggered at the same frontier region" % msg.recovery_behavior_name,
        )
        self.current_goal_blacklisted = True


if __name__ == "__main__":
    rospy.init_node("neo_workshop_frontier_goal_guard")
    FrontierGoalGuard()
    rospy.spin()
