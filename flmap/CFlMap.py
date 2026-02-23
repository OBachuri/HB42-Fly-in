import sys
import re
from typing import Any, cast
from enum import Enum
import heapq
from pydantic import BaseModel, Field, model_validator, field_validator
from pydantic import ConfigDict


# Use an Enum for zone types to manage related constants effectively
class EZoneStatus(Enum):
    PRIORITY = 1000
    NORMAL = 1001
    RESTRICTED = 2000
    BLOCKED = 999999


class ELocation(Enum):
    HUB = "hub"
    START_HUB = "start_hub"
    END_HUB = "end_hub"


class CArea(BaseModel):
    """ Area / Zone / Hub / Point - vertex of graph """

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    x: int
    y: int
    location: ELocation = ELocation.HUB
    zone: EZoneStatus = EZoneStatus.NORMAL
    color: str = ""
    max_drones: int = Field(ge=1, default=1)    # Max quantity of drons
    occupied: dict[int, int] = {}  # how many drons ocupated on every step
    links: list[tuple['CLink', 'CArea', int]] = []  # (Clink, where, max_drons)

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, CArea):
            return False
        return self.name == other.name

    @field_validator("zone", mode="before")
    @classmethod
    def parse_zone(cls, v: Any) -> EZoneStatus | Any:
        if isinstance(v, str):
            try:
                z_ = EZoneStatus[v.upper()]
                return z_
            except ValueError:
                raise ValueError(f"Unexpected format for zone: '{v}'")
        return v

    @model_validator(mode='after')
    def validator(self) -> 'CArea':
        # if self.x <= 0:
        #     print("Error: The zones coordinates will always "
        #           "be positive integers! "
        #           f"(x='{self.x}' for zone name='{self.name}')! ",
        #           file=sys.stderr)
        # if self.y <= 0:
        #     print("Error: The zones coordinates will always "
        #           "be positive integers! "
        #           f"(y='{self.y}' for zone name='{self.name}')! ",
        #           file=sys.stderr)
        if self.name.find("-") >= 0:
            raise ValueError("Error: Dashe in zone names!"
                             f"(dashe fond in hub name '{self.name}')! ")
        if self.name.find(" ") >= 0:
            raise ValueError("Error: Spase in zone names!"
                             f"(spase fond in hub name '{self.name}')! ")
        return self


class CLink(BaseModel):
    """ Edge / link - connection betweeen two Vertices (hubs) """

    model_config = ConfigDict(frozen=True)

    hubs: list[CArea]   # there must be two areas (hubs)
    max_link_capacity: int = Field(ge=1, default=1)
    # how many drons ocupated on every step (time, quantity)
    occupied: dict[int, int] = {}


class CFlMap(BaseModel):
    """ Map (Graph) """
    name: str = Field(min_length=1)
    nb_drones: int = 0
    start_hub: CArea | None = None   # start point
    end_hub: CArea | None = None     # finish point
    hubs: dict[str, CArea] = {}
    links: list[CLink] = []
    drones_path: list[list[CArea | tuple[CArea, CArea]]] = []
    x_min: int | None = None
    x_max: int | None = None
    y_min: int | None = None
    y_max: int | None = None

    def add_hub(self, name: str, x: int, y: int, **params: Any) -> None:
        if len(name.strip()) < 1:
            raise ValueError(f"Error: Hub name must be set ('{name}')!")
        if not (self.hubs.get(name, None) is None):
            raise ValueError(f"Error: Duplicate hub name: '{name}')!")
        area = CArea(name=name, x=x, y=y, **params)
        if (area.location == ELocation.START_HUB):
            if self.start_hub is None:
                self.start_hub = area
            else:
                raise ValueError("Error: More that one start hub "
                                 f"('{self.start_hub.name}' "
                                 f"and  '{area.name}')! ")
        elif (area.location == ELocation.END_HUB):
            if self.end_hub is None:
                self.end_hub = area
            else:
                raise ValueError("Error: More that one end hub "
                                 f"('{self.end_hub.name}' "
                                 f"and  '{area.name}')! ")
        self.hubs[name] = area
        if (self.x_min is None) or (self.x_min > x):
            self.x_min = x
        if (self.x_max is None) or (self.x_max < x):
            self.x_max = x
        if (self.y_min is None) or (self.y_min > y):
            self.y_min = y
        if (self.y_max is None) or (self.y_max < y):
            self.y_max = y

    def add_link(self, hub_name_1: str, hub_name_2: str,
                 max_link_capacity: int = 1) -> None:
        hub_1 = self.hubs.get(hub_name_1, None)
        if hub_1 is None:
            raise ValueError("Error: Can`t create link. "
                             f"Hub '{hub_name_1}' not found!")
        hub_2 = self.hubs.get(hub_name_2, None)
        if hub_2 is None:
            raise ValueError("Error: Can`t create link. "
                             f"Hub '{hub_name_2}' not found!")
        # print("---link---", hub_name_1, hub_name_2)
        # print("1:", hub_1)
        # print("2:", hub_2)
        if len([l_ for l_ in self.links if (hub_1 in l_.hubs)
                and (hub_2 in l_.hubs)]) > 0:
            raise ValueError(f"Error: Link between '{hub_name_1}'"
                             f" and '{hub_name_2}' already exists !")
        link_ = CLink(hubs=[hub_1, hub_2], max_link_capacity=max_link_capacity)
        self.links.append(link_)
        hub_1.links.append((link_, hub_2, max_link_capacity))
        hub_2.links.append((link_, hub_1, max_link_capacity))

    def read_file(self, path_to_file: str) -> None:

        # Matches lines like:
        # hub: roof1 3 4 [zone=restricted color=red]
        HUB_RE = re.compile(
            r"""
            ^(hub|start_hub|end_hub):  # prefix
            \s+(\S+)                   # name
            \s+(-?\d+)                 # first number x
            \s+(-?\d+)                 # second number y
            \s*(\[(.*?)\])?            # optional [something]
            $
            """, re.VERBOSE
            )

        # Matches: connection: hub-roof1 [max_link_capacity=2]
        CONN_RE = re.compile(
            r"^connection:\s+(\S+)-(\S+)\s*(\[(.*?)\])?$"
        )

        # Matches: nb_drones: 5
        SIMPLE_RE = re.compile(
            r"^(\w+):\s+(.+)$"
        )

        def parse_attributes(attr_string: str) -> dict[str, Any]:
            if not attr_string:
                return {}
            parts = attr_string.split()
            attrs = {}
            for p in parts:
                if "=" in p:
                    key, value = p.split("=", 1)
                    attrs[key] = value
            return attrs

        if len(path_to_file) < 1:
            raise ValueError(f"Error: file name not valid ({path_to_file})")
        self.name = path_to_file
        line_numb = 0
        with open(path_to_file) as f:
            for raw in f:
                line = raw.strip()
                line_numb += 1
                if not line or line.startswith("#"):
                    continue
                # print("line:", line_numb, "==:", line)
                # Hubs (including start_hub, end_hub)
                m = HUB_RE.match(line)
                if m:
                    kind, name, x, y, _, attrs_raw = m.groups()
                    atr_ = parse_attributes(attrs_raw)
                    try:
                        x_i = int(x)
                        if x_i <= 0:
                            print("Error: The zones coordinates will always "
                                  "be positive integers! "
                                  f"(x='{x}' for hub name='{name}' "
                                  f"in line {line_numb})! ",
                                  file=sys.stderr)
                    except ValueError as e:
                        print(f"Error: In line {line_numb}"
                              f" for hub {name} wrong value for 'x'.", e,
                              file=sys.stderr)
                        x_i = 0
                    try:
                        y_i = int(y)
                        if y_i <= 0:
                            print("Error: The zones coordinates will always "
                                  "be positive integers! "
                                  f"(y='{y}' for hub name='{name}' "
                                  f"in line {line_numb})! ",
                                  file=sys.stderr)
                    except ValueError as e:
                        print(f"Error: In line {line_numb}"
                              f" for hub {name} wrong value for 'y'.", e,
                              file=sys.stderr)
                        y_i = 0
                    self.add_hub(name=name, x=x_i, y=y_i,
                                 location=kind, **atr_)
                    continue

                # Connections
                m = CONN_RE.match(line)
                if m:
                    h1, h2, _, attrs_raw = m.groups()
                    atr_ = parse_attributes(attrs_raw)
                    self.add_link(h1, h2,
                                  int(atr_.get("max_link_capacity", 1)))
                    continue
                # Simple fields (nb_drones)
                m = SIMPLE_RE.match(line)
                if m:
                    key, value = m.groups()
                    # Handle integer if possible
                    if key == 'nb_drones':
                        try:
                            self.nb_drones = int(value)
                        except ValueError as e:
                            raise ValueError("Quantity of drones (nb_drones)"
                                             "must be positive integer!"
                                             f" line N {line_numb}:"
                                             f" '{line}'", e)
                    continue

                raise ValueError(f"Unrecognized line: {line}")
        if self.nb_drones <= 0:
            raise ValueError("Quantity of drones (nb_drones)"
                             "must be positive integer!")
        if self.start_hub is None:
            raise ValueError("Start hub (start_hub) not found!")
        if self.end_hub is None:
            raise ValueError("Finish hub (end_hub) not found!")

    def find_path_for_one_drone(self,
                                drone_number: int) -> list[CArea |
                                                           tuple[CArea,
                                                                 CArea]]:
        # -> list[tuple[CLink | None, CArea | None]]:
        drone_number

        def reconstruct_path(came_from: dict[CArea, CArea],
                             current: CArea,
                             g_score: dict[CArea, int]
                             ) -> list[CArea | tuple[CArea, CArea]]:
            path: list[CArea | tuple[CArea, CArea]] = [current]  # goal
            time_ = g_score[current]   # arrival time
            while current in came_from:
                from_ = came_from[current]
                time_c = g_score[from_]
                current.occupied[time_] = current.occupied.get(time_, 0) + 1

                link_ = [l_ for l_ in self.links if (from_ in l_.hubs)
                         and (current in l_.hubs)][0]
                if current.zone == EZoneStatus.RESTRICTED:
                    link_.occupied[time_ - 1] = link_.occupied.get(time_ - 1,
                                                                   0) + 1
                    time_step = 2
                else:
                    time_step = 1
                link_.occupied[time_] = link_.occupied.get(time_, 0) + 1
                if current.zone == EZoneStatus.RESTRICTED:
                    path.append((from_, current))
                while time_ > (time_c + time_step):
                    from_.occupied[time_ - time_step] = from_.occupied.get(
                        time_ - time_step, 0) + 1
                    path.append(from_)
                    time_ -= 1
                current = from_
                time_ = time_c
                path.append(current)

                # print("=", current.name, "time:", g_score[current])
            path.reverse()
            return path

        g_score: dict[CArea, int] = {cast(CArea, self.start_hub): 0}

        # open_heap : list[tuple[int, int, int, CArea]]
        # (time, cost/prioritet, counter, zone)
        open_heap: list[tuple[int, int, int, CArea]] = []
        heapq.heappush(open_heap,
                       cast(tuple[int, int, int, CArea],
                            (0, 0, 0, self.start_hub)))
        came_from: dict[CArea, CArea] = {}
        closed = set()

        counter = 0  # prevents tie comparison issues

        while open_heap:
            step_, cost_, _, current = heapq.heappop(open_heap)

            if current == self.end_hub:
                return reconstruct_path(came_from, current, g_score)

            if current in closed:
                continue
            closed.add(current)

            score_ = g_score[current]

            for l_ in current.links:
                link, hub, max_dron_link = l_

                if hub in closed:
                    continue
                if hub.zone == EZoneStatus.BLOCKED:
                    closed.add(hub)
                    continue

                cost_hub = hub.zone.value
                time_ = 1
                if (hub.zone == EZoneStatus.RESTRICTED):
                    time_ = 2
                tentative_g = score_ + time_

                if (hub not in g_score) or g_score[hub] > tentative_g:
                    # check link
                    link_ = [l_ for l_ in self.links if (hub in l_.hubs)
                             and (current in l_.hubs)][0]
                    if link_.max_link_capacity < 1:
                        continue
                    t_ = 0
                    if (hub.zone == EZoneStatus.RESTRICTED):
                        while ((link_.max_link_capacity <=
                                link_.occupied.get(tentative_g + t_, 0))
                                or (link_.max_link_capacity <=
                                    link_.occupied.get(
                                        tentative_g + t_ - 1, 0))
                                or
                                ((hub.max_drones <=
                                  hub.occupied.get(tentative_g + t_, 0))
                                 and (hub != self.end_hub))
                               ):
                            t_ += 1
                    else:
                        while ((link_.max_link_capacity <=
                                link_.occupied.get(tentative_g + t_, 0))
                                or
                                ((hub.max_drones <=
                                 hub.occupied.get(tentative_g + t_, 0))
                                 and (hub != self.end_hub))):
                            t_ += 1
                    g_score[hub] = tentative_g + t_
                    came_from[hub] = current
                    counter += 1
                    # print("cur:", current.name, "---------hub:", hub.name,
                    # "time:", tentative_g + t_,
                    # "cost:", cost_hub, "count:", counter)
                    heapq.heappush(open_heap, (tentative_g + t_,
                                               cost_hub, counter, hub))
        return []

    def find_drones_paths(self) -> None:
        for d_ in range(1, self.nb_drones + 1):
            path_ = self.find_path_for_one_drone(d_)
            self.drones_path.append(path_)
            if len(path_) < 1:
                print("Can`t find path from start to finish")
                return
