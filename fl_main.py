
import sys
import re
from typing import Literal
from typing import Any
from typing import Callable
from enum import Enum
from matplotlib import pyplot as plt
from matplotlib.patches import Circle
from matplotlib.collections import PatchCollection
from matplotlib.colors import is_color_like
from matplotlib.colors import to_rgba

# 1. Define location types using Literal for exact string matching
LocationType = Literal["start_hub", "end_hub", "hub"]
ZONE_LOCATION_TYPES: tuple[LocationType, ...] = ("start_hub", "end_hub", "hub")


# 2. Use an Enum for zone types to manage related constants effectively
class e_ZoneStatus(Enum):
    PRIORITY = 1
    NORMAL = 2
    RESTRICTED = 3
    BLOCKED = 4


ZONE_MAP = {
    "normal": e_ZoneStatus.NORMAL,
    "blocked": e_ZoneStatus.BLOCKED,
    "restricted": e_ZoneStatus.RESTRICTED,
    "priority": e_ZoneStatus.PRIORITY,
}

ZONE_COST = {
    e_ZoneStatus.PRIORITY: 1,
    e_ZoneStatus.NORMAL: 1,
    e_ZoneStatus.RESTRICTED: 2,
    e_ZoneStatus.BLOCKED: 0
}


EXTRA_FIELD_SCHEMA: dict[str, Callable[[Any], tuple[str, Any]]] = {
    # Convert strings → Zone enum
    "zone": lambda v: ("zone", ZONE_MAP[v.lower()]),

    # Convert to int and store as .max
    "max_drones": lambda v: ("max", int(v)),

    # Colors remain direct strings
    "color": lambda v: ("color", str(v)),
}


class c_Area:
    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        location: LocationType = "hub",  # Type hint is the alias
        zone_type: e_ZoneStatus = e_ZoneStatus.NORMAL,  # Type hint is the Enum
        color: str = "",
        max_quantity: int = 1,
        **params_d
    ):
        self.name: str = name
        self.location: LocationType = location
        self.x: int = x
        self.y: int = y
        self.zone: e_ZoneStatus = zone_type
        self.color: str = color
        self.max: int = max_quantity
        # --- apply valid extra fields ---
        for key, value in params_d.items():
            if key not in EXTRA_FIELD_SCHEMA:
                raise ValueError(f"Unknown parameter: {key!r}")
            attr_name, processed_value = EXTRA_FIELD_SCHEMA[key](value)
            setattr(self, attr_name, processed_value)


class c_Link:
    def __init__(
        self,
        area_1: c_Area,
        area_2: c_Area,
        max_link_capacity: int = 1
    ):
        self.area_1 = area_1
        self.area_2 = area_2
        self.max = max_link_capacity


l_areas = list[c_Area]


# Matches lines like:
# hub: roof1 3 4 [zone=restricted color=red]
HUB_RE = re.compile(
    r"^(hub|start_hub|end_hub):\s+(\S+)\s+(-?\d+)\s+(-?\d+)\s*(\[(.*?)\])?$"
)

# Matches: connection: hub-roof1 [max_link_capacity=2]
CONN_RE = re.compile(
    r"^connection:\s+(\S+)-(\S+)\s*(\[(.*?)\])?$"
)

# Matches: nb_drones: 5
SIMPLE_RE = re.compile(
    r"^(\w+):\s+(.+)$"
)


def parse_attributes(attr_string):
    if not attr_string:
        return {}
    parts = attr_string.split()
    attrs = {}
    for p in parts:
        if "=" in p:
            key, value = p.split("=", 1)
            attrs[key] = value
    return attrs

# def draw_dron(data, ax)
#     ax.scatter(x_pos, y_pos, color='green', label="c_Object", marker='x')


def draw_map(data):
    fig, ax = plt.subplots(figsize=(data["x_max"]-data["x_min"] + 2,
                                    data["y_max"]-data["y_min"] + 2))
    ax.set_xlim([data["x_min"] - 2, data["x_max"] + 2])
    ax.set_ylim([data["y_min"] - 2, data["y_max"] + 2])
    ax.set_title("Map: " + data["name"] +
                 " , drones: " + str(data["nb_drones"]))
    for area in data["hubs"].values():
        r = area.max
        if r < 1:
            r = 0.5
        else:
            r = 0.3 + (r - 1) / 20
        if area.color:
            color_ = area.color
            if not is_color_like(color_):
                color_ = '#d4c3d6'
        else:
            color_ = '#e375f0'
        edgecolor_ = None
        # print(area.zone, area.name)
        linewidth_ = None
        if area.zone == e_ZoneStatus.RESTRICTED:
            edgecolor_ = "red"
            linewidth_ = 5
        elif area.zone == e_ZoneStatus.BLOCKED:
            edgecolor_ = '#606060'
            linewidth_ = 10
        elif area.zone.name == "PRIORITY":
            edgecolor_ = "green"
            linewidth_ = 5
        fill_rgba = (*to_rgba(color_)[:3], 0.4)
        if edgecolor_:
            edge_rgba = (*to_rgba(edgecolor_)[:3], 0.9)
        else:
            edge_rgba = edgecolor_
        circle = plt.Circle((area.x, area.y), r, facecolor=fill_rgba,
                            edgecolor=edge_rgba, linewidth=linewidth_)
        ax.add_patch(circle)
        ax.text(area.x, area.y, area.name, ha='center', va='center',
                color='black', fontsize=10, rotation=45,
                rotation_mode='anchor')
    for link in data["connections"]:
        ax.plot([link.area_1.x, link.area_2.x],
                [link.area_1.y, link.area_2.y],
                color='black', lw=(link.max * 2), alpha=0.3)
    plt.show()


def parse_file(path):
    data = {
        "nb_drones": None,
        "hubs": {},
        "connections": [],
        "x_min": None,
        "x_max": None,
        "y_min": None,
        "y_max": None,
        "name": str
    }

    data["name"] = path
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            # Hubs (including start_hub, end_hub)
            m = HUB_RE.match(line)
            if m:
                kind, name, x, y, _, attrs_raw = m.groups()
                atr_ = parse_attributes(attrs_raw)
                # print(atr_)
                x = int(x)
                y = int(y)
                if data["hubs"]:
                    if x > data["x_max"]:
                        data["x_max"] = x
                    if x < data["x_min"]:
                        data["x_min"] = x
                    if y > data["y_max"]:
                        data["y_max"] = y
                    if y < data["y_min"]:
                        data["y_min"] = y
                else:
                    data["x_min"] = x
                    data["x_max"] = x
                    data["y_min"] = y
                    data["y_max"] = y
                data["hubs"][name] = c_Area(name, x, y, kind, **atr_)
                if name.find("-") > 0:
                    print("Error: The connection syntax forbids dashes"
                          " in zone names! "
                          f"(dashe fond in hub name '{name}')! ",
                          file=sys.stderr)
                if (x < 0):
                    print("Error: The zones coordinates will always "
                          "be positive integers! "
                          f"(x='{x}' for zone name='{name}')! ",
                          file=sys.stderr)
                if (y < 0):
                    print("Error: The zones coordinates will always"
                          "be positive integers! "
                          f"(y='{y}' for zone name='{name}')! ",
                          file=sys.stderr)
                continue
            # Connections
            m = CONN_RE.match(line)
            if m:
                a, b, _, attrs_raw = m.groups()
                a = data["hubs"][a]
                b = data["hubs"][b]
                atr_ = parse_attributes(attrs_raw)
                data["connections"].append(
                    c_Link(a, b,
                           int(atr_.get("max_link_capacity", 1))))
                continue

            # Simple fields (nb_drones)
            m = SIMPLE_RE.match(line)
            if m:
                key, value = m.groups()
                # Handle integer if possible
                try:
                    value = int(value)
                except ValueError:
                    pass
                data[key] = value
                continue

            raise ValueError(f"Unrecognized line: {line}")

    return data


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 ", sys.argv[0], " <config_file>")
        sys.exit(1)
    config = parse_file(sys.argv[1])
    draw_map(config)


if __name__ == "__main__":
    main()
