#!/usr/bin/env python3
"""Stop the robot when the link to the control center is lost (dissertation §3.4, §4.2.4; D-50).

Why it exists. The dissertation's dead-man chain says a fallen bridge does not leave the robot in
motion, and that on a bridge failure "the robot - by force of the dead-man mechanism on the
simulation side - ceases motion" within one watchdog interval. The controller's velocity timeout
covers a lost teleoperation stream, but not autonomous navigation: move_base runs here, next to the
robot, and keeps driving an accepted goal whatever happens to the bridge. This node is the
simulation-side half of the dead-man for that case.

What it does. The backend publishes a heartbeat (std_msgs/UInt32) on /robot/web_link/heartbeat ten
times a second through rosbridge and the ROS1<->ROS2 bridge, so the heartbeat arrives only while the
whole chain backend -> rosbridge -> bridge -> this ROS master is alive. Once a heartbeat has been
seen (the node is "armed"):

  * silence longer than STOP_AFTER_S (0.3 s, the watchdog interval of §3.4): engage the twist_mux lock
    `link_loss` (priority 254, just under the operator's emergency stop at 255), which zeroes the
    velocity output whatever move_base or any other input says;
  * silence longer than CANCEL_AFTER_S (3 s, the backend route engine's own stale-status limit):
    cancel every move_base goal, so the robot does not resume a stale goal on its own when the link
    returns - the route engine re-issues the interrupted step (Table 3.2);
  * heartbeat back: release the lock.

It publishes its state ("ok" / "lost") on /robot/web_link/state twice a second for the backend, and
writes every transition as one JSON line to /var/log/robco/link_supervisor.jsonl (measurement data
for experiment E4: copy it, never edit it).

It never touches the emergency-stop lock (robotnik_base_hw/emergency_stop), which belongs to the
operator. Before the first heartbeat it does nothing, so the simulation can be used without the
control center.
"""
import json
import os
import threading
import time

import rospy
from actionlib_msgs.msg import GoalID
from std_msgs.msg import Bool, String, UInt32

HEARTBEAT = "/robot/web_link/heartbeat"
STATE = "/robot/web_link/state"
LOCK = "/robot/link_supervisor/lock"
CANCEL = "/robot/move_base/cancel"
LOG = "/var/log/robco/link_supervisor.jsonl"

STOP_AFTER_S = float(os.environ.get("LINK_STOP_AFTER_S", "0.3"))
CANCEL_AFTER_S = float(os.environ.get("LINK_CANCEL_AFTER_S", "3.0"))
TICK_S = 0.02
STATE_PERIOD_S = 0.5


class Supervisor:
    def __init__(self):
        self.lock = threading.Lock()
        self.last_beat = None  # monotonic time of the last heartbeat
        self.lost = False
        self.cancelled = False
        self.lock_pub = rospy.Publisher(LOCK, Bool, queue_size=1, latch=True)
        self.cancel_pub = rospy.Publisher(CANCEL, GoalID, queue_size=1)
        self.state_pub = rospy.Publisher(STATE, String, queue_size=1)
        rospy.Subscriber(HEARTBEAT, UInt32, self.on_beat, queue_size=10)

    def log(self, event, **fields):
        line = {"t": time.time(), "event": event, **fields}
        try:
            with open(LOG, "a") as handle:
                handle.write(json.dumps(line) + "\n")
        except OSError:
            rospy.logwarn("link_supervisor: cannot write %s", LOG)
        rospy.loginfo("link_supervisor: %s %s", event, fields)

    def on_beat(self, _msg):
        now = time.monotonic()
        with self.lock:
            first = self.last_beat is None
            silence = None if first else now - self.last_beat
            self.last_beat = now
            was_lost = self.lost
            self.lost = False
            self.cancelled = False
        if first:
            self.lock_pub.publish(Bool(False))
            self.log("armed")
        elif was_lost:
            self.lock_pub.publish(Bool(False))
            self.log("recovered", silence_s=round(silence, 3))

    def tick(self):
        now = time.monotonic()
        with self.lock:
            if self.last_beat is None:
                return
            silence = now - self.last_beat
            stop = not self.lost and silence > STOP_AFTER_S
            cancel = self.lost and not self.cancelled and silence > CANCEL_AFTER_S
            if stop:
                self.lost = True
            if cancel:
                self.cancelled = True
        if stop:
            self.lock_pub.publish(Bool(True))
            self.log("lost", silence_s=round(silence, 3))
        if cancel:
            self.cancel_pub.publish(GoalID())  # an empty id cancels every goal
            self.log("goals_cancelled", silence_s=round(silence, 3))

    def state(self):
        with self.lock:
            text = "lost" if self.lost else ("ok" if self.last_beat is not None else "unarmed")
        self.state_pub.publish(String(text))


def main():
    rospy.init_node("link_supervisor")
    supervisor = Supervisor()
    supervisor.log("started", stop_after_s=STOP_AFTER_S, cancel_after_s=CANCEL_AFTER_S)
    next_state = 0.0
    rate = rospy.Rate(1.0 / TICK_S)
    while not rospy.is_shutdown():
        supervisor.tick()
        if time.monotonic() >= next_state:
            supervisor.state()
            next_state = time.monotonic() + STATE_PERIOD_S
        rate.sleep()


if __name__ == "__main__":
    main()
