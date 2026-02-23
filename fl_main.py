
import sys
from typing import cast, Any

from matplotlib import pyplot as plt
# from matplotlib.patches import Circle
# from matplotlib.collections import PatchCollection
from matplotlib.colors import is_color_like, to_rgba
from matplotlib.animation import FuncAnimation
# from matplotlib.backend_bases import KeyEvent

from flmap import CFlMap, EZoneStatus, CArea  # CLink, CArea, ELocation


def draw_map(map: CFlMap, max_turs: int) -> None:
    """ Draw map and animate drones fly """
    fig, ax = plt.subplots(figsize=(cast(int, map.x_max) -
                                    cast(int, map.x_min) + 2,
                                    cast(int, map.y_max) -
                                    cast(int, map.y_min) + 2))

    ax.set_xlim((cast(float, map.x_min) - 2, cast(float, map.x_max) + 2))
    ax.set_ylim((cast(float, map.y_min) - 2, cast(float, map.y_max) + 2))
    ax.set_title("Map: " + map.name +
                 " , drones: " + str(map.nb_drones))
    # # 🔹 Static instruction text
    ax.text(
        0.5, 0.02,   # x=middle, y=very bottom
        "Keys: SPACE - pause/resume, Up/Down - run forward/backward, "
        "Left/Right - step backward/forward, "
        "Esc - exit",
        transform=ax.transAxes,
        fontsize=10,
        ha='center',      # horizontal alignment
        va='bottom'       # vertical alignment
    )

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

    print("-"*40)
    dots = []
    labels = []
    for i_ in range(0, map.nb_drones):
        dot, = ax.plot([], [], 'r^', markersize=10)
        dots.append(dot)
        label = ax.text(0, 0,
                        "", color='blue', fontsize=10,
                        ha='center', va='top')
        labels.append(label)

    step_text = ax.text(0.02, 0.95, "Step: 0",
                        transform=ax.transAxes,
                        fontsize=10
                        )

    frame = 0
    paused = False
    direction = 1   # 1 = forward, -1 = backward

    def draw_frame() -> tuple[Any, ...]:
        old_or_current = int(frame/10)
        lab_: dict[tuple[float, float], list[int]] = {}
        for i_ in range(0, len(map.drones_path)):
            p_ = map.drones_path[i_]
            # evaluate coordinates for current or old position
            if len(p_) > old_or_current:
                cur_ = p_[old_or_current]
            else:
                cur_ = p_[len(p_)-1]
            if type(cur_) is tuple:
                t1, t2 = cur_
                x = (t1.x + t2.x) / 2
                y = (t1.y + t2.y) / 2
            else:
                x = cast(CArea, cur_).x
                y = cast(CArea, cur_).y
            # evaluate coordinates for target position
            r_ = frame % 10
            if (r_ > 0) and (len(p_) > old_or_current + 1):
                cur_ = p_[old_or_current+1]
                if type(cur_) is tuple:
                    t1, t2 = cur_
                    t_x = (t1.x + t2.x) / 2
                    t_y = (t1.y + t2.y) / 2
                else:
                    t_x = cast(CArea, cur_).x
                    t_y = cast(CArea, cur_).y
                x = x + r_*(t_x-x)/10
                y = y + r_*(t_y-y)/10
            if not (x, y) in lab_:
                lab_[(x, y)] = []
            lab_[(x, y)].append(i_)
            dots[i_].set_data([x], [y])
            labels[i_].set_position((x, y-0.15))
            labels[i_].set_text(f"D{i_ + 1}")
        for k_ in lab_.keys():
            if len(lab_[k_]) > 1:
                l_ = list(lab_[k_])
                l_.sort()
                s_ = f"D{l_[0]+1}"
                for i_ in range(1, len(l_)):
                    s_ = s_+f",{l_[i_] + 1}"
                    labels[l_[i_]].set_text("")
                labels[l_[0]].set_text(s_)
                # print(lab_[k_], "s:", s_)
        step_text.set_text(f"Step: {frame/10:.1f}")
        return (*dots, *labels, step_text)

    def update(_: int) -> tuple[Any, ...]:
        nonlocal frame

        if not paused:
            frame += direction
            frame = max(0, min(frame, max_turs))

        return draw_frame()

    # KeyEvent
    def on_key(event: Any) -> None:
        nonlocal paused, frame, direction

        if event.key == ' ':
            paused = not paused

        elif event.key == 'escape':
            plt.close(fig)   # close this specific figure
            return

        elif event.key == 'right':
            paused = True
            frame = min(frame + 1, max_turs)
            draw_frame()
            fig.canvas.draw_idle()

        elif event.key == 'left':
            paused = True
            frame = max(frame - 1, 0)
            draw_frame()
            fig.canvas.draw_idle()

        elif event.key == 'up':
            direction = 1
            paused = False

        elif event.key == 'down':
            direction = -1
            paused = False

    ani = FuncAnimation(fig, update, interval=40,
                        save_count=max_turs, blit=True)

    ani

    fig.canvas.mpl_connect('key_press_event', on_key)

    plt.show()


def main() -> None:
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
                print(f"D{d_+1}-{cast(CArea, s_).name}", end="")
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

    draw_map(m_map, (t_-1)*10)


if __name__ == "__main__":
    main()
