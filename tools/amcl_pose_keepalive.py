#!/usr/bin/env python3
"""Keep the last AMCL pose available to whoever connects late.

AMCL publishes /robot/amcl_pose only when it updates, and it updates only when the robot has moved.
A stationary robot is therefore silent, and the operator console — which learns the pose from the
topic stream — opens to "awaiting localisation" and no marker until somebody drives the robot.
ROS 1 papers over this with a latched topic, but ros1_bridge republishes into ROS 2 as a volatile
topic, so the latched sample never reaches a late subscriber (ros2 topic info -v: VOLATILE).

This node closes the gap from the ROS 1 side. It listens to the pose and, once a second, publishes
the most recent one again on the same topic.

What it deliberately does NOT do:
  * It never touches AMCL. A forced no-motion update per second would resample a stationary
    filter again and again, collapse the particle cloud and shrink the covariance the console and
    the experiments read as localisation quality. Re-sending a stored message changes nothing in
    the filter.
  * It never invents a pose. The message is re-sent unmodified, header stamp included, so the
    age of the estimate stays readable and anything that insists on a fresh pose (the point
    capture forces an update and checks the stamp) is not fooled.
  * It does not outlive AMCL. If nothing but this node publishes the topic, it stays quiet: a
    dead localiser must show as no pose, not as a stale one that keeps arriving.
"""
import rosgraph
import rospy
from geometry_msgs.msg import PoseWithCovarianceStamped

TOPIC = "/robot/amcl_pose"
PERIOD_S = 1.0


def amcl_is_publishing(master, own_name):
    """True while some node other than this one advertises the pose topic."""
    try:
        publishers = master.getSystemState()[0]
    except Exception:  # master unreachable: say nothing rather than guess
        return False
    for topic, nodes in publishers:
        if topic == TOPIC:
            return any(node != own_name for node in nodes)
    return False


def main():
    rospy.init_node("amcl_pose_keepalive")
    own_name = rospy.get_name()
    master = rosgraph.Master(own_name)
    last = {"message": None}

    def remember(message):
        last["message"] = message

    rospy.Subscriber(TOPIC, PoseWithCovarianceStamped, remember, queue_size=1)
    publisher = rospy.Publisher(TOPIC, PoseWithCovarianceStamped, queue_size=1)
    rospy.loginfo("re-sending the last %s once per %.1f s while AMCL is alive", TOPIC, PERIOD_S)

    while not rospy.is_shutdown():
        message = last["message"]
        if message is not None and amcl_is_publishing(master, own_name):
            publisher.publish(message)
        rospy.sleep(PERIOD_S)


if __name__ == "__main__":
    main()
