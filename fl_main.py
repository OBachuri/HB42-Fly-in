
import sys
from typing import cast
from matplotlib import pyplot as plt
# from matplotlib.patches import Circle
# from matplotlib.collections import PatchCollection
from matplotlib.colors import is_color_like
from matplotlib.colors import to_rgba
from flmap import CFlMap, EZoneStatus  # CLink, CArea, ELocation


def draw_map(map: CFlMap):
    fig, ax = plt.subplots(figsize=(cast(int, map.x_max) -
                                    cast(int, map.x_min) + 2,
                                    cast(int, map.y_max) -
                                    cast(int, map.y_min) + 2))

    ax.set_xlim((cast(float, map.x_min) - 2, cast(float, map.x_max) + 2))
    ax.set_ylim((cast(float, map.y_min) - 2, cast(float, map.y_max) + 2))
    ax.set_title("Map: " + map.name +
                 " , drones: " + str(map.nb_drones))
    for area in map.hubs.values():
        dr = area.max_drones
        if dr < 1:
            r = 0.5
        else:
            r = 0.3 + (dr - 1) / 20
        if area.color:
            color_ = area.color
            if not is_color_like(color_):
                color_ = '#d4c3d6'
        else:
            color_ = '#e375f0'
        edgecolor_ = None
        # print(area.zone, area.name)
        linewidth_ = None
        if area.zone == EZoneStatus.RESTRICTED:
            edgecolor_ = "red"
            linewidth_ = 5
        elif area.zone == EZoneStatus.BLOCKED:
            edgecolor_ = '#606060'
            linewidth_ = 10
        elif area.zone == EZoneStatus.PRIORITY:
            edgecolor_ = "green"
            linewidth_ = 5
        fill_rgba = (*to_rgba(color_)[:3], 0.4)
        edge_rgba: None | str | tuple[float, float, float, float] = edgecolor_
        if edgecolor_:
            edge_rgba = (*to_rgba(edgecolor_)[:3], 0.9)
        circle = plt.Circle((area.x, area.y), r, facecolor=fill_rgba,
                            edgecolor=edge_rgba, linewidth=linewidth_)
        ax.add_patch(circle)
        ax.text(area.x, area.y, area.name, ha='center', va='center',
                color='black', fontsize=10, rotation=45,
                rotation_mode='anchor')
    for link in map.links:
        ax.plot([link.hubs[0].x, link.hubs[1].x],
                [link.hubs[0].y, link.hubs[1].y],
                color='black', lw=(link.max_link_capacity * 2), alpha=0.3)
    plt.show()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 ", sys.argv[0], " <config_file>")
        sys.exit(1)

    file_name = sys.argv[1]
    m_map = CFlMap(name=file_name)
    m_map.read_file(file_name)

    print("-"*20)
    # print("hubs:", m_map.hubs)
    # print("-"*20)
    # print("links:", m_map.links)

    # path = find_path(config)
    # print(path)

    m_map.find_drones_paths()

    t_ = 1
    not_the_end = True
    while not_the_end:
        not_the_end = False
        print_space = False
        for d_ in range(0, m_map.nb_drones):
            p_ = m_map.drones_path[d_]
            if len(p_) < t_ + 1:
                continue
            s_ = p_[t_]
            not_the_end = True
            if s_ == p_[t_-1]:
                continue
            if print_space:
                print(" ", end="")
            print_space = True
            if type(s_) is tuple:
                t1, t2 = s_
                print(f"D{d_+1}-{t1.name}-{t2.name}", end="")
            else:
                print(f"D{d_+1}-{s_.name}", end="")
        if not_the_end:
            print()
            t_ += 1

    print(f"{m_map.nb_drones} drones arrived in {t_-1} turns.")

    # for d_ in range(1, m_map.nb_drones + 1):
    #     print(f"----D{d_}")
    #     path_ = m_map.find_path_for_one_drone(d_)
    #     m_map.drones_path.append(path_)
    #     if len(path_) < 1:
    #         print("Can`t find path from start to finish")
    #     else:
    #     # for i_ in path_.keys():
    #     #     print(path_[i_].name, "->", i_.name)
    #         j = 0
    #         print(f"---- Path D{d_}:")
    #         for i_ in path_:
    #             if type(i_) is tuple:
    #                 t1, t2 = i_
    #                 print(j, f"{t1.name}-{t2.name}")
    #             else:
    #                 print(j, i_.name)
    #             j += 1
    # for l_ in m_map.links:
    #     if len(l_.occupied) > 0:
    #         print(f"L:{l_.hubs[0].name}-{l_.hubs[1].name} :", l_.occupied)

    # for h_ in m_map.hubs.values():
    #     if len(h_.occupied) > 0:
    #         print(f"H:{h_.name}:", h_.occupied)

    draw_map(m_map)


if __name__ == "__main__":
    main()
