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
    capture forces an update and requires a newer stamp) is not fooled.
  * It does not outlive AMCL, and it does not outlive THIS run of AMCL. It remembers only a
    message that /robot/amcl itself published (the connection header names the sender, so its own
    re-sends and the bridge's are ignored), and it asks /robot/amcl for its process id every
    period. If the node is gone, does not answer, or answers with a different process id, the
    remembered pose is dropped and nothing is sent until the new AMCL publishes. A dead or
    restarted localiser must show as no pose, not as the previous run's pose that keeps arriving
    (a SLAM session replaces the localiser; replaying the pose from before it is wrong).
"""
import xmlrpc.client

import rosgraph
import rospy
from geometry_msgs.msg import PoseWithCovarianceStamped

TOPIC = "/robot/amcl_pose"
AMCL_NODE = "/robot/amcl"
PERIOD_S = 1.0
PROBE_TIMEOUT_S = 0.5


class _TimeoutTransport(xmlrpc.client.Transport):
    """XML-RPC over a connection that gives up quickly: a hung node must not stall the loop."""

    def make_connection(self, host):
        connection = super().make_connection(host)
        connection.timeout = PROBE_TIMEOUT_S
        return connection


def amcl_pid(master, own_name):
    """The process id of the running /robot/amcl, or None when it is gone or does not answer."""
    try:
        uri = master.lookupNode(AMCL_NODE)
        proxy = xmlrpc.client.ServerProxy(uri, transport=_TimeoutTransport())
        code, _, pid = proxy.getPid(own_name)
    except Exception:  # not registered, master unreachable, node hung or dead
        return None
    return pid if code == 1 else None


def main():
    rospy.init_node("amcl_pose_keepalive")
    own_name = rospy.get_name()
    master = rosgraph.Master(own_name)
    state = {"message": None, "pid": None, "header_warned": False}

    def remember(message):
        header = getattr(message, "_connection_header", None)
        if header is None:
            # rospy internal; if it ever disappears, accept the sample but only while the
            # process probe passes (the loop below), and say so once.
            if not state["header_warned"]:
                state["header_warned"] = True
                rospy.logwarn("no connection header on %s; accepting samples while %s answers",
                              TOPIC, AMCL_NODE)
        elif header.get("callerid") != AMCL_NODE:
            return
        state["message"] = message

    rospy.Subscriber(TOPIC, PoseWithCovarianceStamped, remember, queue_size=1)
    publisher = rospy.Publisher(TOPIC, PoseWithCovarianceStamped, queue_size=1)
    rospy.loginfo("re-sending the last %s once per %.1f s while this run of %s is alive",
                  TOPIC, PERIOD_S, AMCL_NODE)

    while not rospy.is_shutdown():
        pid = amcl_pid(master, own_name)
        if pid is None:
            state["message"] = None
            state["pid"] = None
        elif pid != state["pid"]:
            if state["pid"] is not None:
                # A known run was replaced between two probes. (When no run was known the
                # sample held so far is the latched one delivered at subscribe time, or one the
                # new run just published; both are legitimate and are kept.)
                rospy.loginfo("%s restarted (pid %s -> %s); dropping the remembered pose",
                              AMCL_NODE, state["pid"], pid)
                state["message"] = None
            state["pid"] = pid
        message = state["message"]
        if message is not None:
            publisher.publish(message)
        rospy.sleep(PERIOD_S)


if __name__ == "__main__":
    main()
