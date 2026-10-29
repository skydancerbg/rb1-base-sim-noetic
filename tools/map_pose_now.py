#!/usr/bin/env python3
"""Print a pose as one line of JSON: {"x", "y", "yaw", "stamp"}. Exit 1 if there is none.

  map_pose_now.py
      The robot's pose in the map frame right now, from the transform robot_map -> robot_base_footprint
      (the frames of rb1_base_localization/launch/amcl.launch). While AMCL runs, this is AMCL's estimate;
      while gmapping runs, it is gmapping's. That is why a stop can read it BEFORE it kills gmapping and
      hand it to the localiser as a starting pose (plan step 2.2).

  map_pose_now.py --amcl-after [--timeout 15]
      Ask AMCL for a no-motion update, then print the first /robot/amcl_pose whose stamp is later than
      the pose held when it asked. A replayed pose (the keepalive, a latched sample) carries an older stamp
      and is not accepted: this answers "has the localiser really produced a pose since I asked".
"""
import argparse
import json
import math
import sys

import rospy

MAP_FRAME = "robot_map"
BASE_FRAME = "robot_base_footprint"
POSE_TOPIC = "/robot/amcl_pose"
UPDATE_SERVICE = "/robot/request_nomotion_update"


def yaw_of(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def tf_pose(timeout):
    import tf2_ros

    buffer = tf2_ros.Buffer()
    tf2_ros.TransformListener(buffer)
    transform = buffer.lookup_transform(MAP_FRAME, BASE_FRAME, rospy.Time(0), rospy.Duration(timeout))
    t = transform.transform
    return {"x": t.translation.x, "y": t.translation.y, "yaw": yaw_of(t.rotation),
            "stamp": transform.header.stamp.to_sec()}


def amcl_pose_after_update(timeout):
    from geometry_msgs.msg import PoseWithCovarianceStamped
    from std_srvs.srv import Empty

    # "Newer" means a stamp later than the pose already held when we ask, the same rule the backend
    # applies to a point capture. Not "later than the moment of the request": the first update after
    # the request uses a laser scan that was stamped a few tens of milliseconds BEFORE it.
    try:
        held = rospy.wait_for_message(POSE_TOPIC, PoseWithCovarianceStamped, timeout=2.0).header.stamp
    except rospy.ROSException:
        held = None  # nothing held: any pose that arrives after the request is new
    asked_at = rospy.Time.now()
    rospy.wait_for_service(UPDATE_SERVICE, timeout=5.0)
    rospy.ServiceProxy(UPDATE_SERVICE, Empty)()
    deadline = rospy.Time.now() + rospy.Duration(timeout)
    while rospy.Time.now() < deadline:
        try:
            message = rospy.wait_for_message(POSE_TOPIC, PoseWithCovarianceStamped, timeout=1.0)
        except rospy.ROSException:
            continue
        stamp = message.header.stamp
        if (stamp > held) if held is not None else (stamp >= asked_at):
            p = message.pose.pose
            return {"x": p.position.x, "y": p.position.y, "yaw": yaw_of(p.orientation),
                    "stamp": stamp.to_sec()}
    raise RuntimeError("no %s newer than the update request arrived within %.0f s" % (POSE_TOPIC, timeout))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--amcl-after", action="store_true")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    rospy.init_node("map_pose_now", anonymous=True, disable_signals=True)
    try:
        pose = amcl_pose_after_update(args.timeout) if args.amcl_after else tf_pose(args.timeout)
    except Exception as exc:  # noqa: BLE001 - one line on stderr, exit 1, that is the contract
        print("map_pose_now: %s" % exc, file=sys.stderr)
        return 1
    print(json.dumps(pose))
    return 0


if __name__ == "__main__":
    sys.exit(main())
