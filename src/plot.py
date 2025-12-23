import math
from dataclasses import dataclass
from svgpathtools import svg2paths
import serial
import time


@dataclass
class PlotterSettings:
    """
    holds all plotter attributes
    """

    port: str = ""
    baud: int = 0
    knife_offset: float = 0.0
    speed: int = 0
    pressure: int = 0
    scale: float = 100.0


PORT = "/dev/ttyUSB0"  # Linux example
# PORT = "/dev/ttyACM0"
# PORT = "COM3"            # Windows example

BAUDRATE = 9600

hpgl_data = "IN;\nSP1;\nPU0,0;\nPD1000,0;\nPU;\nSP0;\n"


def send_hpgl(port, baudrate, data):
    with serial.Serial(
        port=port,
        baudrate=baudrate,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False,
    ) as ser:
        time.sleep(2)  # give plotter time to wake up

        print("Sending HPGL...")
        ser.write(data.encode("ascii"))
        ser.flush()

        time.sleep(0.5)
        print("Done.")


class Vinyl_cutter:
    def __init__(self):
        self.speed: int = 14
        self.pressure: int = 100
        self.knife_offset: float = 0.2
        self.port: str = "/dev/ttyUSB0"


# -----------------------------
# Utilities (same as before)
# -----------------------------


def distance(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.hypot(dx, dy)


def lerp(p1, p2, t):
    return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))


# -----------------------------
# Flatten cubic Bezier from svgpathtools CubicBezier
# -----------------------------


def flatten_cubic_bezier(p0, p1, p2, p3, max_chord=0.05, min_depth=5):
    points = [p0]

    def chord_error(p0, p1, p2, p3):
        def point_line_dist(p, a, b):
            if a == b:
                return distance(p, a)
            t = (
                (p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])
            ) / distance(a, b) ** 2
            t = max(0, min(1, t))
            proj = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
            return distance(p, proj)

        return max(point_line_dist(p1, p0, p3), point_line_dist(p2, p0, p3))

    def recursive_flatten(p0, p1, p2, p3, depth=0):
        err = chord_error(p0, p1, p2, p3)
        if err <= max_chord or depth >= min_depth:
            points.append(p3)
        else:
            p01 = lerp(p0, p1, 0.5)
            p12 = lerp(p1, p2, 0.5)
            p23 = lerp(p2, p3, 0.5)
            p012 = lerp(p01, p12, 0.5)
            p123 = lerp(p12, p23, 0.5)
            p0123 = lerp(p012, p123, 0.5)
            recursive_flatten(p0, p01, p012, p0123, depth + 1)
            recursive_flatten(p0123, p123, p23, p3, depth + 1)

    recursive_flatten(p0, p1, p2, p3, 0)
    return points


# -----------------------------
# Flatten Line
# -----------------------------


def flatten_line(
    p0,
    p1,
):
    return [p0, p1]


# -----------------------------
# Flatten Quadratic Bezier (from svgpathtools)
# -----------------------------


def flatten_quadratic_bezier(p0, p1, p2, max_chord=0.05, min_depth=5):
    # Convert to cubic: P0,P1,P2 → P0,P01,P12,P2
    c1 = (p0[0] + 2 / 3 * (p1[0] - p0[0]), p0[1] + 2 / 3 * (p1[1] - p0[1]))
    c2 = (p2[0] + 2 / 3 * (p1[0] - p2[0]), p2[1] + 2 / 3 * (p1[1] - p2[1]))
    return flatten_cubic_bezier(
        p0, c1, c2, p2, max_chord=max_chord, min_depth=min_depth
    )


# -----------------------------
# Flatten SVG Path
# -----------------------------


# def flatten_svg_path(path, max_chord=0.05, min_depth=5):
#     """
#     Flatten an SVG path into a homogeneous list of points with pen up/down flags.
#     Returns a list of tuples: (pen, x, y), where 0=PU, 1=PD
#     """
#     points = []
#     start_point = None
#
#     for seg in path:
#         # If start of segment is different from previous end, move pen up
#         if seg.start != start_point and start_point is not None:
#             points.append((0, seg.start.real, seg.start.imag))  # PU
#         start_point = seg.end
#
#         # Flatten the segment according to its type
#         if seg.__class__.__name__ == "Line":
#             pts = flatten_line(
#                 (seg.start.real, seg.start.imag), (seg.end.real, seg.end.imag)
#             )
#         elif seg.__class__.__name__ == "CubicBezier":
#             pts = flatten_cubic_bezier(
#                 (seg.start.real, seg.start.imag),
#                 (seg.control1.real, seg.control1.imag),
#                 (seg.control2.real, seg.control2.imag),
#                 (seg.end.real, seg.end.imag),
#                 max_chord=max_chord,
#                 min_depth=min_depth,
#             )
#         elif seg.__class__.__name__ == "QuadraticBezier":
#             pts = flatten_quadratic_bezier(
#                 (seg.start.real, seg.start.imag),
#                 (seg.control.real, seg.control.imag),
#                 (seg.end.real, seg.end.imag),
#                 max_chord=max_chord,
#                 min_depth=min_depth,
#             )
#         elif seg.__class__.__name__ == "Arc":
#             pts = []
#             for b in seg.as_cubic_curves():
#                 pts += flatten_cubic_bezier(
#                     (b.start.real, b.start.imag),
#                     (b.control1.real, b.control1.imag),
#                     (b.control2.real, b.control2.imag),
#                     (b.end.real, b.end.imag),
#                     max_chord=max_chord,
#                     min_depth=min_depth,
#                 )[1:]  # skip duplicate start
#         else:
#             continue
#
#         # Append points as pen down
#         for i, (x, y) in enumerate(pts):
#             if i == 0 and points and points[-1][1:] == (x, y):
#                 continue  # avoid duplicating previous point
#             points.append((1, x, y))  # PD
#     if points:
#         pen, x, y = points[-1]
#         points[-1] = (0, x, y)
# return points


def flatten_svg_path(path, max_chord=0.05, min_depth=5):
    """
    Flatten an SVG path into a homogeneous list of points with pen up/down flags.
    Returns a list of tuples: (pen, x, y), where 0=PU, 1=PD.
    Ensures knife is up before and after each path object.
    """
    points = []

    # Start of path: move pen up to the first point
    if len(path) == 0:
        return points

    first_seg = path[0]
    points.append((0, first_seg.start.real, first_seg.start.imag))  # PU

    start_point = first_seg.end
    for seg in path:
        # If segment is disconnected from previous, lift pen
        if seg.start != start_point:
            points.append((0, seg.start.real, seg.start.imag))  # PU

        start_point = seg.end

        # Flatten segment
        if seg.__class__.__name__ == "Line":
            pts = flatten_line(
                (seg.start.real, seg.start.imag), (seg.end.real, seg.end.imag)
            )
        elif seg.__class__.__name__ == "CubicBezier":
            pts = flatten_cubic_bezier(
                (seg.start.real, seg.start.imag),
                (seg.control1.real, seg.control1.imag),
                (seg.control2.real, seg.control2.imag),
                (seg.end.real, seg.end.imag),
                max_chord=max_chord,
                min_depth=min_depth,
            )
        elif seg.__class__.__name__ == "QuadraticBezier":
            pts = flatten_quadratic_bezier(
                (seg.start.real, seg.start.imag),
                (seg.control.real, seg.control.imag),
                (seg.end.real, seg.end.imag),
                max_chord=max_chord,
                min_depth=min_depth,
            )
        elif seg.__class__.__name__ == "Arc":
            pts = []
            for b in seg.as_cubic_curves():
                pts += flatten_cubic_bezier(
                    (b.start.real, b.start.imag),
                    (b.control1.real, b.control1.imag),
                    (b.control2.real, b.control2.imag),
                    (b.end.real, b.end.imag),
                    max_chord=max_chord,
                    min_depth=min_depth,
                )[1:]  # skip duplicate start
        else:
            continue

        # Append flattened points as pen down
        for i, (x, y) in enumerate(pts):
            points.append((1, x, y))  # PD

    # End of path: lift pen at the last point
    if points:
        last_x, last_y = points[-1][1], points[-1][2]
        points.append((0, last_x, last_y))  # PU

    return points


# def flatten_svg_path(path, max_chord=0.05, min_depth=5):
#     points = []
#     start_point = None
#     for seg in path:
#         pen = 1
#         if seg.start != start_point and start_point is not None:
#             # Move pen to new start
#             pen = 0
#             points.append((pen, seg.start.real, seg.start.imag))
#
#         start_point = seg.end
#         if seg.__class__.__name__ == "Line":
#             pts = flatten_line(
#                 (seg.start.real, seg.start.imag), (seg.end.real, seg.end.imag)
#             )
#         elif seg.__class__.__name__ == "CubicBezier":
#             pts = flatten_cubic_bezier(
#                 (seg.start.real, seg.start.imag),
#                 (seg.control1.real, seg.control1.imag),
#                 (seg.control2.real, seg.control2.imag),
#                 (seg.end.real, seg.end.imag),
#                 max_chord=max_chord,
#                 min_depth=min_depth,
#             )
#         elif seg.__class__.__name__ == "QuadraticBezier":
#             pts = flatten_quadratic_bezier(
#                 (seg.start.real, seg.start.imag),
#                 (seg.control.real, seg.control.imag),
#                 (seg.end.real, seg.end.imag),
#                 max_chord=max_chord,
#                 min_depth=min_depth,
#             )
#         elif seg.__class__.__name__ == "Arc":
#             # Convert Arc to cubic Bezier approximation using svgpathtools
#             bez_list = seg.as_cubic_curves()
#             pts = []
#             for b in bez_list:
#                 pts += flatten_cubic_bezier(
#                     (b.start.real, b.start.imag),
#                     (b.control1.real, b.control1.imag),
#                     (b.control2.real, b.control2.imag),
#                     (b.end.real, b.end.imag),
#                     max_chord=max_chord,
#                     min_depth=min_depth,
#                 )[1:]
#         else:
#             continue
#         print("pts", pts)
#         if points and isinstance(points[-1], tuple) and points[-1][0] == 0:
#             # Already moved
#             points += pts[1:]
#         else:
#             points += pts
#     return points


# -----------------------------
# Generate HP-GL commands
# -----------------------------


def generate_hpgl_from_points(points, scale=2):
    """
    Generate HPGL commands from points.
    points: list of (pen, x, y) tuples, 0=PU, 1=PD
    scale: multiplier to convert SVG units to plotter units
    """
    cmds = []
    pen_down = False

    for pen, x, y in points:
        x_scaled = int(x * scale)
        y_scaled = int(y * scale)

        if pen == 0:  # PU
            cmds.append(f"PU {x_scaled},{y_scaled};")
            pen_down = False
        else:  # PD
            if not pen_down:
                cmds.append(f"PD {x_scaled},{y_scaled};")
                pen_down = True
            else:
                cmds.append(f"PD {x_scaled},{y_scaled};")

    return cmds


def angle_between(p1, p2, p3):
    """Return the angle (in degrees) at p2 formed by p1-p2-p3"""
    v1 = (p1[1] - p2[1], p1[2] - p2[2])
    v2 = (p3[1] - p2[1], p3[2] - p2[2])
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    mag1 = math.hypot(*v1)
    mag2 = math.hypot(*v2)
    if mag1 * mag2 == 0:
        return 180.0
    cos_angle = max(min(dot / (mag1 * mag2), 1), -1)
    return math.degrees(math.acos(cos_angle))


def apply_drag_knife_offset(points, offset):
    """
    Adjust points for a drag knife.
    points: list of (pen, x, y)
    offset: distance to overshoot/shorten at non-tangent joins
    """
    adjusted = points.copy()

    for i in range(1, len(points) - 1):
        prev_pt = points[i - 1]
        curr_pt = points[i]
        next_pt = points[i + 1]

        # Only consider points where pen is down
        if curr_pt[0] == 1 and prev_pt[0] == 1 and next_pt[0] == 1:
            ang = angle_between(prev_pt, curr_pt, next_pt)
            if ang < 179.9:  # non-tangent join
                # Compute overshoot vector along prev-curr
                dx1 = curr_pt[1] - prev_pt[1]
                dy1 = curr_pt[2] - prev_pt[2]
                length1 = math.hypot(dx1, dy1)
                if length1 != 0:
                    dx1 *= offset / length1
                    dy1 *= offset / length1
                    adjusted[i] = (curr_pt[0], curr_pt[1] + dx1, curr_pt[2] + dy1)

                # Compute shorten vector along curr-next
                dx2 = next_pt[1] - curr_pt[1]
                dy2 = next_pt[2] - curr_pt[2]
                length2 = math.hypot(dx2, dy2)
                if length2 != 0:
                    dx2 *= offset / length2
                    dy2 *= offset / length2
                    adjusted[i + 1] = (next_pt[0], next_pt[1] - dx2, next_pt[2] - dy2)

    return adjusted


# def generate_hpgl_from_points(points, scale=100):
#     cmds = []
#     pen_down = False
#     for pt in points:
#         if isinstance(pt, tuple) and pt[0] == "PU":
#             x, y = pt[1]
#             cmds.append(f"PU {int(x * scale)},{int(y * scale)};")
#             pen_down = False
#         else:
#             x, y = pt
#             if not pen_down:
#                 cmds.append(f"PD {int(x * scale)},{int(y * scale)};")
#                 pen_down = True
#             else:
#                 cmds.append(f"PD {int(x * scale)},{int(y * scale)};")
#     return cmds


def send_to_plotter(attr: object, file):
    """
    sends the data to the plotter
    """
    # parse the svg file
    paths, _attributes = svg2paths(file)
    all_points = []

    # flatten cuves
    for path in paths:
        pts = flatten_svg_path(path, max_chord=0.05, min_depth=5)
        all_points += pts

    # compensate drag knife
    if attr.knife_offset != 0:
        all_points = apply_drag_knife_offset(all_points, attr.knife_offset)

    # move points to the right lower corner
    min_x = min(x for pen, x, y in all_points)
    min_y = min(y for pen, x, y in all_points)
    normalized_points = [(pen, x - min_x, y - min_y) for pen, x, y in all_points]

    # generate hpgl code from the points
    hpgl_cmds = build_header(attr)
    hpgl_cmds += "\n".join(
        generate_hpgl_from_points(
            normalized_points,
            # scale=attr.scale,
            scale=20,
        )
    )
    hpgl_cmds += "SO;"
    print(hpgl_cmds)
    send_hpgl(attr.port, attr.baud, hpgl_cmds)


def build_header(attr: object):
    """
    returns a string with the header for the hpgl file
    """
    header = "SO;IN; !PG0;PA ;SP1;\n"
    header += "VS1PU 3307,0; PD 3307,0; PU 0,0;"
    header += f"VS{attr.speed};\n"
    header += f"FS{ui_to_fs(attr.pressure)};\n"
    return header


def ui_to_fs(ui_value: float) -> int:
    """
    Convert UI slider value to FS plotter pressure command.

    Piecewise linear mapping:
    50 → 7, 100 → 17, 200 → 27
    """
    if ui_value <= 100:
        fs = 0.2 * ui_value - 3
    else:
        fs = 0.1 * ui_value + 7
    return int(round(fs))


# -----------------------------
# Example usage
# -----------------------------
if __name__ == "__main__":
    # Load SVG file
    svg_file = "example.svg"  # replace with your SVG
    paths, _attributes = svg2paths(svg_file)
    # for obj in paths:
    #     for segment in obj:
    # print(obj)

    all_points = []
    for path in paths:
        pts = flatten_svg_path(path, max_chord=0.05, min_depth=5)
        all_points += pts

    all_points = apply_drag_knife_offset(all_points, 0.2)
    # Find the minimum X and Y across all points
    min_x = min(x for pen, x, y in all_points)
    min_y = min(y for pen, x, y in all_points)

    # Shift all points so that (min_x, min_y) becomes (0,0)
    normalized_points = [(pen, x - min_x, y - min_y) for pen, x, y in all_points]
    # print(all_points)
    hpgl_cmds = generate_hpgl_from_points(normalized_points, scale=10)

    # for cmd in hpgl_cmds:
    #     print(cmd)
    cmd_str = "\n".join(hpgl_cmds)

    hpgl_data = "SO;IN; !PG0;PA ;SP1;VS1PU 3307,0; PD 3307,0; PU 0,0; VS40; FS10"

    hpgl_data += cmd_str
    print(hpgl_data)
    send_hpgl(PORT, BAUDRATE, hpgl_data)

    # Output HP-GL
    with open("output.hpgl", "w") as f:
        f.write("IN;\n")
        for cmd in hpgl_cmds:
            f.write(cmd + "\n")
        f.write("SO;\n")

    print("HP-GL generated:", len(hpgl_cmds), "commands")
