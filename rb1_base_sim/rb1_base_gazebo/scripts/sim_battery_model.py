#!/usr/bin/env python3
"""A declared *model* of the robot's battery. It is not a measurement of one.

**Why this exists.** This simulation publishes no battery topic — confirmed twice against a fully
loaded world (plan step P0.2), which is why `docs/ros_interface_inventory.md` recorded the
auto-dock step P4.2 as untestable. That note gave the owner two options: drop the feature, or
"add a battery model to the Gazebo robot as first-class world-modelling work". This is that
option, taken on 05.08.2026. The third possibility it explicitly ruled out — publishing a made-up
percentage into the operator interface — is *not* what happens here, and the difference is the
whole point: nothing invents a reading downstream of the robot. The robot's simulation gains a
modelled component, and everything after it reads that component honestly, exactly as it reads a
modelled laser or a modelled camera.

**What P4.2 may therefore claim, and what it may not.** Measurable and real: that the threshold
latches, that hysteresis prevents flapping, that the active goal is cancelled through the
navigation stack's own mechanism, that the robot reaches the station, that every console sees it.
Not claimable from anything here: endurance, runtime, range, or how long an RB-1 actually lasts.
Those are properties of a physical battery, and this node knows nothing about one.

**The energy model**, deliberately the simplest thing that makes the decision path testable:

    P(t) = idle_watts + watts_per_mps·|v| + watts_per_radps·|ω|

integrated against a capacity in watt-hours, with the commanded velocity taken from the topic the
controller actually receives, so a robot that is *told* to move spends energy even if it is
wedged against a wall. Every coefficient is a parameter with a stated default; none is measured,
and none should ever be cited as if it were.

**Time compression.** A battery that takes hours to discharge cannot be exercised in an
experiment, so `time_scale` multiplies modelled time. The default is 8, which empties a full pack
in roughly an hour of real time at idle — slow enough that a soak is not spent at 0 %, fast enough
that a discharge is reachable inside a session. Anything that needs the threshold *now* should use
`~set_level` rather than a larger scale, because a scale high enough to be convenient makes every
other number on the topic change faster than an operator can read it. `time_remaining` is
published in **real** minutes — what an observer will actually wait — because a number on a screen
meaning "minutes, but only in a time frame we compressed" is a trap. Set `time_scale` to 1.0 for a
model that runs in physical time.

**What is left empty on purpose.** `cell_voltages` stays an empty array: this models a battery,
not eight cells, and filling it with plausible per-cell numbers would be precisely the
fabrication the data policy forbids. An empty array says "not modelled"; eight invented floats
would say "measured".

**Two topics, one state, and why.** The primary topic keeps the robot's own vocabulary —
`robotnik_msgs/BatteryStatus`, the type the RB-1 stack uses — so nothing here invents an interface
the hardware would not have. But that type **cannot cross the ROS 1 → ROS 2 bridge**: the bridge
on this deployment knows 168 message pairs and `robotnik_msgs` is not one of them (there is no ROS
2 build of it), so a browser or the backend would never see a byte of it. `sensor_msgs/BatteryState`
*is* in the pairs, so the same model state is mirrored there. The mirror is a translation, never a
second source of truth: both messages are built from one tick of one model.

Where `BatteryState` asks for something this model does not know, it says so rather than guessing:
temperature is `NaN` (the field's documented "unmeasured"), the chemistry is `UNKNOWN`, and the
per-cell arrays stay empty. Charge and capacity are derived from the model's own watt-hours at the
nominal voltage, which is arithmetic on a declared parameter, not a measurement.

**Fault injection.** `~set_level` puts the charge anywhere instantly (drive the threshold without
waiting for it), and `~set_charging` toggles charging. EXP-09's fault matrix and P4.2's acceptance
both need to reach a low battery on demand rather than on the model's schedule.
"""

import threading

import rospy
from geometry_msgs.msg import Twist
from robotnik_msgs.msg import BatteryStatus
from robotnik_msgs.srv import set_float_value, set_float_valueResponse
from sensor_msgs.msg import BatteryState
from std_msgs.msg import String
from std_srvs.srv import SetBool, SetBoolResponse

#: Below this, the model reports the pack as empty rather than going negative.
MIN_LEVEL = 0.0
MAX_LEVEL = 100.0


class SimBatteryModel(object):
    def __init__(self):
        # --- the model's parameters. Defaults are choices, not measurements. -------------------
        self._capacity_wh = float(rospy.get_param("~capacity_wh", 480.0))
        self._nominal_voltage = float(rospy.get_param("~nominal_voltage", 24.0))
        self._voltage_full = float(rospy.get_param("~voltage_full", 25.2))
        self._voltage_empty = float(rospy.get_param("~voltage_empty", 21.0))
        self._idle_watts = float(rospy.get_param("~idle_watts", 60.0))
        self._watts_per_mps = float(rospy.get_param("~watts_per_mps", 120.0))
        self._watts_per_radps = float(rospy.get_param("~watts_per_radps", 40.0))
        self._charge_watts = float(rospy.get_param("~charge_watts", 300.0))
        self._time_scale = float(rospy.get_param("~time_scale", 8.0))
        self._level = float(rospy.get_param("~initial_level", 100.0))

        # A command that stopped arriving is not a command that is still being obeyed. twist_mux
        # discards an input silent for 0.5 s (measured, P0.2) — the model follows the controller
        # rather than keeping the last Twist forever.
        self._command_timeout = float(rospy.get_param("~command_timeout", 0.5))

        rate_hz = float(rospy.get_param("~rate_hz", 1.0))
        cmd_topic = rospy.get_param("~cmd_vel_topic", "robotnik_base_control/cmd_vel")
        topic = rospy.get_param("~topic", "battery")

        self._charging = bool(rospy.get_param("~initial_charging", False))
        self._lock = threading.Lock()
        self._cmd = (0.0, 0.0)
        self._cmd_stamp = None
        self._last_tick = None

        self._publisher = rospy.Publisher(topic, BatteryStatus, queue_size=1)
        # The bridgeable mirror. See the module docstring: robotnik_msgs does not cross to ROS 2,
        # so without this the console and the backend would see nothing at all.
        self._state_publisher = rospy.Publisher(
            rospy.get_param("~state_topic", "battery_state"), BatteryState, queue_size=1
        )
        # Read by nothing in the control path: it exists so that anyone who finds these topics —
        # an operator, a probe, a reviewer — is told what produced them without having to know
        # which node was running. Latched *and* repeated: latching does not survive every bridge
        # hop, and a disclosure a client never receives discloses nothing.
        self._disclosure = rospy.Publisher("battery_source", String, queue_size=1, latch=True)
        self._disclosure_period = float(rospy.get_param("~disclosure_period", 10.0))
        rospy.Subscriber(cmd_topic, Twist, self._on_cmd, queue_size=10)

        rospy.Service("~set_level", set_float_value, self._on_set_level)
        rospy.Service("~set_charging", SetBool, self._on_set_charging)

        statement = (
            "simulated battery model (not a measurement): capacity {:.0f} Wh, "
            "idle {:.0f} W, {:.0f} W per m/s, {:.0f} W per rad/s, time_scale {:g}x"
        ).format(
            self._capacity_wh,
            self._idle_watts,
            self._watts_per_mps,
            self._watts_per_radps,
            self._time_scale,
        )
        self._statement = statement
        self._disclosure.publish(String(data=statement))
        rospy.loginfo("sim_battery_model: %s", statement)

        self._timer = rospy.Timer(rospy.Duration(1.0 / rate_hz), self._tick)
        self._disclosure_timer = rospy.Timer(
            rospy.Duration(self._disclosure_period),
            lambda _event: self._disclosure.publish(String(data=self._statement)),
        )

    # --- inputs ---------------------------------------------------------------------------------

    def _on_cmd(self, msg):
        with self._lock:
            self._cmd = (abs(msg.linear.x) + abs(msg.linear.y), abs(msg.angular.z))
            self._cmd_stamp = rospy.Time.now()

    def _on_set_level(self, request):
        value = float(request.value)
        if not MIN_LEVEL <= value <= MAX_LEVEL:
            return set_float_valueResponse(
                ret=False,
                errorMessage=String(data="level must be between 0 and 100, got {}".format(value)),
            )
        with self._lock:
            self._level = value
        rospy.logwarn("sim_battery_model: level set to %.1f%% by request (fault injection)", value)
        return set_float_valueResponse(ret=True, errorMessage=String(data=""))

    def _on_set_charging(self, request):
        with self._lock:
            self._charging = bool(request.data)
        state = "charging" if request.data else "discharging"
        rospy.loginfo("sim_battery_model: %s by request", state)
        return SetBoolResponse(success=True, message=state)

    # --- the model ------------------------------------------------------------------------------

    def _draw_watts(self, now):
        """Power drawn right now, in watts. Negative means the pack is being filled."""
        if self._charging:
            return -self._charge_watts
        linear, angular = self._cmd
        if self._cmd_stamp is None or (now - self._cmd_stamp).to_sec() > self._command_timeout:
            linear = angular = 0.0
        return self._idle_watts + self._watts_per_mps * linear + self._watts_per_radps * angular

    def _tick(self, _event):
        now = rospy.Time.now()
        with self._lock:
            if self._last_tick is None:
                self._last_tick = now
                return
            # Wall-clock seconds since the last tick. ROS time here is simulated time, which is
            # what should drive a model of the simulated robot; the multiplication by time_scale
            # is the only place the model deviates from it, and it is declared.
            elapsed = (now - self._last_tick).to_sec()
            self._last_tick = now
            if elapsed <= 0.0:
                return

            watts = self._draw_watts(now)
            delta_wh = watts * (elapsed * self._time_scale) / 3600.0
            self._level = max(
                MIN_LEVEL, min(MAX_LEVEL, self._level - 100.0 * delta_wh / self._capacity_wh)
            )
            level, charging = self._level, self._charging

        message = BatteryStatus()
        message.level = level
        message.is_charging = charging
        message.voltage = self._voltage_empty + (self._voltage_full - self._voltage_empty) * (
            level / 100.0
        )
        # Amperes at the modelled voltage. Positive while discharging, negative while charging,
        # which is the sign convention of the field's own comment ("in amperes", with is_charging
        # carrying the direction).
        message.current = watts / max(message.voltage, 1e-6)
        remaining_wh = self._capacity_wh * level / 100.0

        if charging:
            missing_wh = self._capacity_wh - remaining_wh
            message.time_charging = self._minutes(missing_wh, self._charge_watts)
            message.time_remaining = 0
        else:
            message.time_charging = 0
            message.time_remaining = self._minutes(remaining_wh, watts)
        # Deliberately empty: this models a pack, not its cells. See the module docstring.
        message.cell_voltages = []

        self._publisher.publish(message)
        self._state_publisher.publish(self._as_battery_state(message, remaining_wh, charging))

    def _as_battery_state(self, status, remaining_wh, charging):
        """The same tick as `sensor_msgs/BatteryState`, the only form that crosses the bridge."""
        state = BatteryState()
        state.header.stamp = rospy.Time.now()
        state.voltage = status.voltage
        state.current = -status.current  # BatteryState: negative while discharging
        state.percentage = status.level / 100.0  # BatteryState is a fraction, not a percentage
        state.design_capacity = self._capacity_wh / self._nominal_voltage  # Ah, from the model
        state.capacity = state.design_capacity
        state.charge = remaining_wh / self._nominal_voltage
        # Not modelled, and the field's own documentation says to say so with NaN rather than to
        # supply a plausible number.
        state.temperature = float("nan")
        state.power_supply_status = (
            BatteryState.POWER_SUPPLY_STATUS_CHARGING
            if charging
            else BatteryState.POWER_SUPPLY_STATUS_DISCHARGING
        )
        state.power_supply_health = BatteryState.POWER_SUPPLY_HEALTH_GOOD
        # No chemistry is modelled; claiming one would be inventing a property of a pack that does
        # not exist.
        state.power_supply_technology = BatteryState.POWER_SUPPLY_TECHNOLOGY_UNKNOWN
        state.present = True
        state.cell_voltage = []
        state.cell_temperature = []
        return state

    def _minutes(self, energy_wh, watts):
        """Real minutes until `energy_wh` is gone at `watts`, accounting for time compression."""
        if watts <= 0.0:
            return 0
        modelled_minutes = 60.0 * energy_wh / watts
        return int(max(0.0, modelled_minutes / max(self._time_scale, 1e-6)))


def main():
    rospy.init_node("sim_battery_model")
    SimBatteryModel()
    rospy.spin()


if __name__ == "__main__":
    main()
