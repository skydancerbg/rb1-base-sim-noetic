#!/usr/bin/env python3
"""Navigation regression check for the RB-1 in neo_workshop.

Drives a there-and-back move_base goal pair and reports, as JSON, the outcome of each
goal, its duration, the number of recovery behaviours triggered and two oscillation
proxies (reverse-velocity samples and angular sign flips). Written for plan step P0.6,
where the inspection mast gained 0.27 kg and the verified navigation tuning had to be
shown unaffected; reusable as the navigation half of any later regression run.

Usage:  python3 tools/nav_regression_test.py <label>
Writes: /tmp/nav_<label>.json

Requires a running simulation with the navigation stack up. Wait for
`rostopic hz /robot/front_laser/scan` to read ~33 Hz before starting: the neo_workshop
world holds 204 models and the robot spawns well after roscore.
"""
import sys, time, math, json
import rospy, actionlib
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from geometry_msgs.msg import Twist
from rosgraph_msgs.msg import Log

label = sys.argv[1] if len(sys.argv) > 1 else "run"
goals = [(2.5, 0.0, 0.0), (0.0, 0.0, 0.0)]

rospy.init_node("nav_test", anonymous=True, disable_signals=True)

# With use_sim_time the node must see /clock before any rospy.Duration wait is meaningful.
_t0 = time.time()
while rospy.Time.now().to_sec() == 0.0 and time.time() - _t0 < 30:
    time.sleep(0.2)
print("sim clock = %.1f" % rospy.Time.now().to_sec())

stats = {"recoveries": [], "cmd_samples": 0, "rev_samples": 0,
         "max_lin": 0.0, "max_ang": 0.0, "sign_flips": 0}
_last_sign = [0]

def on_cmd(msg):
    stats["cmd_samples"] += 1
    stats["max_lin"] = max(stats["max_lin"], abs(msg.linear.x))
    stats["max_ang"] = max(stats["max_ang"], abs(msg.angular.z))
    if msg.linear.x < -0.01:
        stats["rev_samples"] += 1
    s = 1 if msg.angular.z > 0.05 else (-1 if msg.angular.z < -0.05 else 0)
    if s != 0 and _last_sign[0] != 0 and s != _last_sign[0]:
        stats["sign_flips"] += 1
    if s != 0:
        _last_sign[0] = s

def on_log(msg):
    t = msg.msg.lower()
    if any(k in t for k in ("recovery", "clearing costmap", "aborting", "oscillation", "stuck")):
        stats["recoveries"].append(msg.msg.strip()[:120])

rospy.Subscriber("/robot/move_base/cmd_vel", Twist, on_cmd)
rospy.Subscriber("/rosout_agg", Log, on_log)

client = actionlib.SimpleActionClient("/robot/move_base", MoveBaseAction)
if not client.wait_for_server(rospy.Duration(30)):
    print("RESULT " + json.dumps({"error": "move_base action server not available"}))
    sys.exit(1)

results = []
for i, (gx, gy, gyaw) in enumerate(goals):
    g = MoveBaseGoal()
    g.target_pose.header.frame_id = "robot_map"
    g.target_pose.header.stamp = rospy.Time.now()
    g.target_pose.pose.position.x = gx
    g.target_pose.pose.position.y = gy
    g.target_pose.pose.orientation.z = math.sin(gyaw / 2.0)
    g.target_pose.pose.orientation.w = math.cos(gyaw / 2.0)
    t0 = time.time()
    client.send_goal(g)
    ok = client.wait_for_result(rospy.Duration(180))
    dt = time.time() - t0
    state = client.get_state()
    results.append({"goal": [gx, gy], "reached": bool(ok) and state == 3,
                    "state": int(state), "seconds": round(dt, 1)})
    print("goal %d (%.1f, %.1f): state=%d in %.1fs" % (i, gx, gy, state, dt))
    time.sleep(2)

out = {"label": label, "goals": results,
       "recoveries": len(stats["recoveries"]),
       "recovery_msgs": stats["recoveries"][:8],
       "cmd_samples": stats["cmd_samples"], "reverse_samples": stats["rev_samples"],
       "angular_sign_flips": stats["sign_flips"],
       "max_lin": round(stats["max_lin"], 3), "max_ang": round(stats["max_ang"], 3)}
print("RESULT " + json.dumps(out))
open("/tmp/nav_%s.json" % label, "w").write(json.dumps(out, indent=2))
