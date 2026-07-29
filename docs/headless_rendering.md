# Headless rendering — why the cameras need a virtual display

## Symptom

Gazebo runs, navigation works, the laser publishes at 33 Hz — but **no camera topic ever
appears**. Neither the inspection webcam (`/robot/usb_cam/image_raw`) nor the Orbbec Astra
publishes anything, even though both sensors are present in the robot description and both
links spawn in Gazebo. Nothing in the `roslaunch` output points at a camera.

The failure is silent in the place that matters: everything a mobile base needs keeps working,
so the absence is easy to misread as a missing sensor or a broken plugin.

## Cause

This VM is headless: no X server, and until 29.07.2026 no virtual framebuffer either. With no
display, Gazebo cannot initialise OGRE, and camera sensors are never created. `gzserver.log`
says so directly:

```
[Err] [RenderEngine.cc:749] Cannot open display:
[Wrn] [RenderEngine.cc:89]  Unable to create X window. Rendering will be disabled
[Wrn] [RenderEngine.cc:292] Cannot initialize render engine since render path type is NONE.
[Err] [DepthCameraSensor.cc:66] Unable to create DepthCameraSensor. Rendering is disabled.
[Err] [CameraSensor.cc:125] Unable to create CameraSensor. Rendering is disabled.
```

`libgazebo_ros_camera.so` then has no sensor to attach to, so it advertises nothing. Both
cameras fail identically because the fault is in the render engine, not in either sensor.

A misleading detail: `gz topic -l` **does** list
`/gazebo/default/robot/robot_base_footprint/robot_usb_cam_sensor/image`. Those are names
declared from the SDF, not evidence of rendering — `gz topic -e` on them returns no data.
Do not take that listing as proof that Gazebo is rendering.

## Fix

A virtual framebuffer, provided by `xvfb.service` (installed 29.07.2026):

```
/usr/bin/Xvfb :99 -screen 0 1280x1024x24 +extension GLX +extension RENDER -noreset
```

It is enabled at boot. Rendering is software (Mesa `llvmpipe`); this VM has no GPU. Check it
with `systemctl is-active xvfb.service` and `DISPLAY=:99 glxinfo | grep "OpenGL renderer"`.

`tools/run_neo_workshop.sh` resolves a display before every Gazebo launch: it uses `DISPLAY`
if that display exists, otherwise `:99`, otherwise it starts its own Xvfb. If it falls back to
the virtual framebuffer it also passes `launch_rviz:=false`, because nobody can see RViz there
and it competes for the CPU the software renderer needs. Override with `LAUNCH_RVIZ=true`.

## Measured cost

Software rendering is affordable here (12 vCPU, 31 GB RAM):

| Condition | Gazebo real-time factor | Camera rate |
|---|---|---|
| No subscriber on the camera topic | ~1.44 | not rendering |
| A subscriber on `/robot/usb_cam/image_raw` | ~1.00 | 15.0 Hz |

## A trap worth knowing

`libgazebo_ros_camera` renders **lazily — only while something is subscribed**, and the first
message delivered after subscribing is the **last frame of the previous session**, carrying its
old timestamp. A consumer that connects, grabs one frame and disconnects therefore gets a stale
image, and repeating that yields the same stale image every time no matter how the robot moves.
Anything that inspects frames must hold a persistent subscription and discard the first frame,
or check that `header.stamp` is advancing.
