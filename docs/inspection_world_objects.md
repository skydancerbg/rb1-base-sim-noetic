# Lighting regimes and inspection objects (plan step P5.6)

What the experiments on detection (EXP-04, EXP-05) need from the simulated world, and how to drive it.
Everything is done on the running simulation, so nothing restarts and the `.world` file is untouched.
The scripts live in this repository under `tools/` and are reached from the home directory:

    ~/lighting   -> ~/catkin_ws/src/tools/lighting
    ~/inspection -> ~/catkin_ws/src/tools/inspection

(`ln -sfn ~/catkin_ws/src/tools/lighting ~/lighting`, and likewise for `inspection`, recreates them.)

## Lighting regimes

    ssh sim ~/lighting/set_regime.sh <nominal|dimmed|side>
    ssh sim ~/lighting/set_regime.sh status

| regime | what it sets |
|---|---|
| `nominal` | the world file's own light: sun diffuse 0.8, ambient 0.4, sun direction (-0.5, 0.5, -1) |
| `dimmed` | sun diffuse 0.2, ambient 0.1, same direction |
| `side` | sun diffuse 0.05 and ambient 0.08, plus one point light (`regime_side_lamp`) to the left of the panel and in front of it at camera height: the panel face is lit obliquely, bright on the left and fading to the right |

Done with Gazebo transport messages to the server (`light/modify` for the sun, `scene` for the ambient,
`factory/light` for the side lamp; the lamp is removed by the other two regimes). Values are absolute, so
a regime always gives the same lighting. Every change is appended with a UTC timestamp to
`~/lighting/regime.log`; `current_regime` holds the last one. Wait about 2 s after a change before
capturing.

Why the side regime is a lamp and not a rotated sun: shadows are off in this world (`<shadows>0</shadows>`),
so a directional light lights each flat surface uniformly and a "side" sun only darkens whatever faces
the camera. A nearby point light is what produces the gradient across a face that side lighting means.

## The inspection panel

One board hangs 1.0 m straight ahead of the inspection spot, at the camera's height (1.2 m), with one
object per detection method. The robot is expected at **world (-1.185, 0.524), heading 0** (test spot "a"
in the app's e2e specs; the map frame differs from the Gazebo world frame by about 0.06 m).

    ssh sim ~/inspection/set_state.sh <lamp|dial|display> <norm|anomaly>
    ssh sim ~/inspection/set_state.sh all <norm|anomaly>
    ssh sim ~/inspection/set_state.sh status          # JSON read back from the world
    ssh sim ~/inspection/set_state.sh ensure          # spawn the panel if missing (idempotent)
    ssh sim ~/inspection/set_state.sh park            # robot to the inspection spot, zero velocity
    ssh sim ~/inspection/set_state.sh remove

| object | norm | anomaly | also |
|---|---|---|---|
| indicator lamp | green, lit | red, lit | `off` |
| dial gauge | needle at 40 degrees clockwise from up | 100 degrees | `angle=<degrees>` |
| digital display | reads `42.7` | reads `49.9` | |

The panel is spawned into the running simulation on first use (and again after a simulation restart,
which forgets it). A fresh panel starts in the norm state. `all norm` / `all anomaly` set the three at
once. Each change is appended with a UTC timestamp to `~/inspection/state.log`.

How a state is made, and why it is exactly reproducible: every part is a static model without collision;
a state is an *absolute pose* of some models, never a toggle. The lamp is three spheres at one place, the
one for the state sits there and the others are parked under the floor; the dial is one needle model
rolled about the panel normal; the display is two models with different textures, one parked. The same
argument always gives the same read-back state (`status` reads it from Gazebo, not from a file).

Geometry, against the numbers in the plan: the board is 0.9 m wide, 0.45 m high and 0.06 m deep, centred
at 1.2 m, so everything is above 0.975 m. The laser scan plane is at 0.187 m and nothing is below
0.975 m, so the panel is invisible to the laser, the costmap and AMCL; the map is unaffected. The board's
front face is 0.97 m from the robot's centre at the spot. The mast (at the robot's centre, up to 1.2 m)
could only reach it if the robot drove about 0.97 m forward of the spot; the planner does not know the
panel is there, but the routes used in the tests end at 0.5 m or less from the spot. This is not a
wall-mounted box as in the plan: the world has no wall at this place, so the board floats, which is
harmless for a camera. The lamp is 60 mm across (about 50 px at 1 m), the dial face 180 mm, the display
260 x 100 mm.

## What was measured (and what it does not say)

`~/inspection/verify_p56.py` checks the acceptance on the live camera and saves the evidence frames to
`docs/evidence/p5.6/` (640 x 360): one per regime, and each object in each state. On 03.11.2026 it passed
all 16 checks in four consecutive runs:

- the dimmed and side frames differ from the nominal frame by about 24 and 46 (mean absolute difference,
  0-255 scale), against a noise floor of 0.2 between frames of an unchanged scene; dimmed and side differ
  from each other by about 47; nominal restored matches the original within noise;
- each object's own region changes by 9 to 48 (floor under 4) when its state changes, and no other object's
  read-back state changes;
- the same argument twice gives the same read-back state and a frame within the floor.

Observations worth knowing before using the objects in an experiment:

1. **The simulated robot is not still.** While "idle" it creeps and turns (about 0.1 degree per second
   and 0.3 mm per second at the spot, odometry twist about 1e-3). At 1 m that is a few pixels per second,
   which is enough to put the dial out of the middle of its region and to make two frames of the same
   scene differ. Use `set_state.sh park` before a measurement block and capture a fixed time after it; a
   run of captures that are minutes long drifts off the panel. `park` does not re-seed AMCL.
2. With the robot parked and a fixed delay, the detectors read the objects as intended (indicator lamp
   norm d < 0.01, red 0.77, off 0.42; dial angle within 2 degrees of the commanded one at 60, 180 and 300
   degrees; display `42.7` / `49.9` with Tesseract confidence 62 to 96). These are single runs on this
   panel, not detection rates.
3. The nominal regime overexposes the white wall above and around the panel (the world's light is bright);
   the objects themselves are not saturated.
4. The camera sees the whole room: the panel occupies the middle of the frame, with the wood wall and a
   door opening beside it. Regions of interest must be drawn on the object, not on the frame centre.

## Files

- `tools/lighting/set_regime.sh`
- `tools/inspection/set_state.sh`, `inspection_ctl.py` (the models, as SDF built in code, and the states),
  `materials/` (display textures and the Ogre material script), `verify_p56.py`
- `docs/evidence/p5.6/*.jpg`
