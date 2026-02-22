*This project has been created as part of the 42 curriculum by obachuri.*

---

# Fly-in - Drone Routing Simulation


This project is part of the 42.fr curriculum.

---

The task - in the shortest time drive all given drones from the start point to the finish.

We have a map - a graph where: 
Vertex (hub, zone, arrea) - plase where drones can be some time.
propetis:
- max_drones(default: 1) - Maximum drones that can occupy this zone simultaneously
- zone_type (normal, blocked, restricted, priority)

Edge (connection, link) - connection between two Vertices.
propetis:
- max_link_capacity(default: 1) - Maximum drones that can traverse this connection simultaneously

Each movement between hubs has a cost in turns, based on the zone_type of the destination hub:
- normal: 1 turn (default)
- restricted: 2 turns
- priority: 1 turn (but should be preferred in pathfinding algorithms)
- blocked: Inaccessible — cannot be entered

## Installation

```bash
make install
```

## Usage

```bash
# Run with map
make run my_map_file.txt
```

### Map File

```bash
# my test map

nb_drones: 5

start_hub: start 0 0 [color=green]
end_hub: goal 10 10 [color=yellow]
hub: roof1 3 5 [zone=restricted color=red]
hub: roof2 7 2 [zone=normal color=blue]
hub: corridorA 4 3 [zone=priority color=green max_drones=2]
hub: corridorB 5 8 [zone=priority color=green max_drones=4]
hub: tunnelB 7 4 [zone=normal color=red max_drones=2]
hub: obstacleX 5 5 [zone=blocked color=gray]
connection: start-roof1
connection: corridorA-start
connection: roof1-roof2
connection: roof2-tunnelB
connection: corridorA-tunnelB [max_link_capacity=2]
connection: tunnelB-goal  [max_link_capacity=2]
```


## Requirements

- Python 3.10 or later
- Pydantic
- Matplotlib

## License

Part of the 42 curriculum project.