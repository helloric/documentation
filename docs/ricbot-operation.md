# RICbot Operation

This page describes the practical startup workflow for operating the RICbot
with the Docker-based ROS 2 setup from this repository.

The robot itself runs only the hardware-facing drivers. A separate control
machine(like your laptop) runs the operator tools and ROS 2 services:

- Zenoh router for ROS 2 communication.
- RViz for visualization and interaction.
- Cartographer for mapping.
- Nav2 for navigation with a saved map.
- Map saving tools for writing generated maps back into the repository.

For deeper details about individual components, use the dedicated sections in
the documentation navigation, especially **Navigation** and **AI**.
This page focuses on the order of commands needed to bring up the system.

## System Layout

The setup is split across two machines:

- **Control machine:** a developer workstation, lab PC, or laptop that has this
  repository checked out and runs the operator-side Docker containers.
- **Robot:** the RICbot machine that runs the hardware driver container and
  connects back to the Zenoh router on the control machine.

The startup order matters: the `zenoh_router` container must already be running
on the control machine before the robot driver is started.

## Requirements

- Docker and Docker Compose.
- `tmux` on the control machine.
- X11 or Xwayland forwarding for RViz. The environment may need to be adjusted
  depending on the operating system and display setup.
- SSH access to the robot.
- The robot and control machine must be on the same network.

If Docker reports that `/tmp/.X11-unix` is not shared from the host, allow
`/tmp` in Docker Desktop file sharing settings or run the setup on a native
Linux Docker engine. The RViz container needs that socket to open its window.
The launcher scripts create `/tmp/.docker.xauth` automatically so RViz can
authenticate to the host X11/Xwayland display, and allow local root X11 access
with `xhost` when the command is available.

## Robot Startup

Start the control-machine workflow first, either [map recording](#create-a-map)
or [navigation](#navigate-with-a-saved-map), so the `zenoh_router` container is
already running before the robot driver tries to connect.

Find the control machine IP address with `ip a` or `ifconfig`. Then SSH into
the robot and start the robot driver container:

```bash
bash start_ricbot.bash <control-machine-ip>
```
Where `<control-machine-ip>` is IP address of your machine.

The script sets the robot container's Zenoh endpoint to the Zenoh router on the
control machine. If you need to set the endpoint manually, use:

```bash
ZENOH_CONNECT_ENDPOINT=tcp/<control-machine-ip>:7447 docker compose up ricbot
```

If the robot cannot connect, first check that `zenoh_router` is still running on
the control machine and that the IP address is reachable from the robot.

## Create a Map

From the repository root on the control machine, run:

```bash
bash map_recorder.bash
```

This opens a `tmux` session with two panes:

- Left pane: starts `zenoh_router`, RViz, Cartographer, and keyboard teleop.
- Right pane: opens a shell inside the Cartographer/Nav2 container for saving
  the map.

Once the left pane has started `zenoh_router`, start the robot driver from the
robot using the steps in [Robot Startup](#robot-startup).

Use the teleop pane to drive the robot through the area. The teleop container
starts with conservative speeds, currently `0.2` linear and `0.8` angular.

When the map looks correct in RViz, save it from the right pane:

```bash
ros2 run nav2_map_server map_saver_cli -f /map_data/<map_name>
```

This writes `<map_name>.yaml` and the map image into
`ricbot_navigation/maps/` on the control machine.


## Navigate With a Saved Map

From the repository root on the control machine, run:

```bash
bash navigation.bash
```

By default this loads:

```text
./map_data/rh1_eg_new_map.yaml
```

To use another map in `ricbot_navigation/maps/`, pass either the map base name
or the full container path:

```bash
bash navigation.bash rh1_eg_map
bash navigation.bash ./map_data/rh1_et1_map.yaml
```

You can also set the map with an environment variable:

```bash
NAV_MAP_YAML=/map_data/rh1_eg_map.yaml bash navigation.bash
```

The navigation script opens a `tmux` session named `navigation`:

- Left pane: `zenoh_router` and RViz.
- Right pane: Nav2 using the selected map.

Once the left pane has started `zenoh_router`, start the robot driver from the
robot using the steps in [Robot Startup](#robot-startup).

In RViz, set the robot's initial pose with `2D Pose Estimate`. The arrow should
point in the robot's forward direction. Once localization matches the map, send
a goal with `2D Goal Pose`.

If localization does not match the visible map, try to give a better initial estimate pose or restart navigation with the correct map file and set the initial pose again before sending a goal.

## Useful Paths

The operation scripts expect to be run from the repository root. These are the
main files and directories that are relevant during mapping and navigation:

- `ricbot_navigation/maps/`: stores saved maps. Each map usually consists of a
  `.yaml` metadata file and an image file. `map_saver_cli` writes new maps here
  through the `/map_data` mount inside the container. Navigation also reads map
  files from this directory.
- `ricbot_navigation/config/nav2_params.yaml`: contains Nav2 configuration such
  as planner, controller, costmap, and localization parameters. Change this
  when navigation behavior needs tuning, for example obstacle inflation,
  controller behavior, or AMCL settings.
- `ricbot_navigation/config/cartographer_2d.lua`: contains the 2D Cartographer
  SLAM configuration used while creating a map. Change this when map building
  quality needs tuning, for example scan matching or trajectory builder
  parameters.
- `compose.yml`: defines the Docker services used by this workflow, including
  `zenoh_router`, `ricbot`, `rviz`, `nav`, `nav_cartographer`, and `teleop`.
  Check this file when changing container images, mounted volumes, devices, or
  Zenoh-related environment variables.
- `map_recorder.bash`: starts the mapping `tmux` session on the control
  machine.
- `navigation.bash`: starts the navigation `tmux` session on the control
  machine.
- `start_ricbot.bash`: Should be run on the robot, and starts the robot-side driver container, and accepts the
  control machine IP address as an optional argument.

## Stopping

Detach from `tmux` with `d`, and then `Ctrl-d`.

Stop the control-machine-side containers with:

```bash
docker compose down
```
