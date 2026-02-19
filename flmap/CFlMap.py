import sys
import re
from typing import Any
from enum import Enum
from pydantic import BaseModel, Field, model_validator, field_validator


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
    name: str = Field(min_length=1)
    x: int
    y: int
    location: ELocation = ELocation.HUB
    zone: EZoneStatus = EZoneStatus.NORMAL
    color: str = ""
    max_drones: int = Field(ge=1, default=1)    # Max quantity of drons

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
    """ Link betweeen two hubs """
    hubs: list[CArea]   # there must be two areas
    max_link_capacity: int = Field(ge=1, default=1)


class CFlMap(BaseModel):
    """ Map """
    name: str = Field(min_length=1)
    nb_drones: int = 0
    start_hub: CArea | None = None   # start point
    end_hub: CArea | None = None     # finish point
    hubs: dict[str, CArea] = {}
    links: list[CLink] = []
    x_min: int | None = None
    x_max: int | None = None
    y_min: int | None = None
    y_max: int | None = None

    def add_hub(self, name: str, x: int, y: int, **params) -> None:
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
        self.links.append(CLink(hubs=[hub_1, hub_2],
                                max_link_capacity=max_link_capacity))

    def read_file(self, path_to_file: str):

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
