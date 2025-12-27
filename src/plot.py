import math
import threading
from math import radians, cos, sin
from svgpathtools import Path, Line, svg2paths
from xml.etree.ElementTree import Element, SubElement, tostring
import serial
import time


class PlotterSettings:
    """
    holds all plotter attributes
    """

    def __init__(self, settings: object):
        self.settings = settings
        self.port: str = ""
        self.baud: int = 0
        self.knife_offset: float = 0.0
        self.speed: int = 0
        self.pressure: int = 0
        self.scale: float = 310.0
        self.load_settings()
        self.thread = None

    def load_settings(self):
        """
        updates the attributes of plotter_attr from
        the values saved to disk (settings popup)
        """
        self.scale = self.settings.settings.value(
            "plot/scale_factor", 200.0, type=float
        )
        self.baud = int(self.settings.settings.value("plot/baud", 9600, type=int))
        self.port = self.settings.settings.value("plot/port", "COM1", type=str)

    def save_settngs(self):
        """
        saves all settings set in settings dialog to disk
        """
        self.settings.settings.setValue("plot/scale_factor", self.scale)
        self.settings.settings.setValue("plot/baud", self.baud)
        self.settings.settings.setValue("plot/port", self.port)

    def plot(self, gfx: object, scale):
        """
        sends the data to the plotter
        """
        # parse the svg file
        paths = gfx.paths
        all_points = []

        # flatten cuves
        for path in paths:
            pts = flatten_svg_path(path, max_chord=0.05, min_depth=5)
            all_points += pts

        # compensate drag knife
        if self.knife_offset != 0:
            all_points = apply_drag_knife_offset(all_points, self.knife_offset)

        # move points to the right lower corner
        min_x = min(x for pen, x, y in all_points)
        min_y = min(y for pen, x, y in all_points)
        normalized_points = [(pen, x - min_x, y - min_y) for pen, x, y in all_points]

        # generate hpgl code from the points
        final_scale = scale * self.scale
        hpgl_cmds = build_header(self)
        hpgl_cmds += "\n".join(
            generate_hpgl_from_points(
                normalized_points,
                # scale=attr.scale,
                scale=final_scale,
            )
        )
        hpgl_cmds += "SO;"
        self.send_hpgl(self.port, self.baud, hpgl_cmds)

    def send_hpgl(self, port, baudrate, data):
        # if self.tread:
        #     self.tread.cancel()

        # self.thread = threading.Thread(target=send_hpgl_tread, args=(port, baudrate, data))
        # self.thread.start()
        # if self.thread:
        #     stop_thread = True
        #     self.thread.join()
        #     self.thread = None
        self.thread = threading.Thread(target=send_hpgl_thread, args=(port, baudrate, data))
        self.thread.daemon = True
        self.thread.start()


class Graphics:
    """
    holds the graphics for manipulation and render
    """

    def __init__(self):
        self.file_name: str = ""
        self.paths = None
        self.attributes = None
        self.svg_xml = None
        self.rotation: float = 0
        self.rot90: bool = False
        self.dim_x: float = 0.0
        self.dim_y: float = 0.0
        self.frame: bool = False

    def load_svg(self, path_to_file, render_color):
        """
        loads an svg file into memory
        """
        self.file_name = path_to_file
        self.paths, self.attributes = svg2paths(self.file_name)
        self.set_outline_mode(render_color)
        dim = self.update()
        return dim

    def set_outline_mode(self, render_color, stroke_width=0.2):
        """
        Enable or disable outline-only rendering.
        Modifies attributes in -place.
        """
        for attr in self.attributes:
            attr.pop("style", None)
            attr["fill"] = "none"
            attr["stroke"] = attr.get("stroke", render_color)
            attr["stroke-width"] = str(stroke_width)

    def update(self):
        svg_elem = Element("svg", xmlns="http://www.w3.org/2000/svg")

        for path, attr in zip(self.paths, self.attributes):
            d = path.d()
            # remove 'd' if it exists in attributes
            attr_copy = dict(attr)
            attr_copy.pop("d", None)
            SubElement(svg_elem, "path", d=d, **attr_copy)
        self.svg_xml = tostring(svg_elem, encoding="utf-8")
        self.bounding_box()
        return self.dim_x, self.dim_y

    def reset(self):
        self.file_name: str = ""
        self.paths = None
        self.attributes = None
        self.svg_xml = None
        self.scale = 1
        self.rotation = 0
        self.rot90 = False
        self.dim_x = 0.0
        self.dim_y = 0.0
        self.frame = False

    def rotate_by_90(self):
        if self.rot90:
            self.rotate(90)
            self.rot90 = False
        else:
            self.rotate(-90)
            self.rot90 = True

    def rotate(self, angle_deg: float, origin=(0, 0)):
        """
        Rotate all paths by angle_deg degrees around a given origin.
        : param angle_deg: rotation angle in degrees
        : param origin: tuple(x, y) to rotate around
        """

        if not self.paths:
            return None  # or (0,0,0,0) if you prefer
        print(angle_deg)
        self.rotation += angle_deg
        # if angle_deg < 0:
        #     angle_deg = 360 - abs(angle_deg)
        # print(angle_deg)
        ox, oy = origin
        angle_rad = radians(angle_deg)
        cos_a = cos(angle_rad)
        sin_a = sin(angle_rad)

        def rotate_point(p):
            x, y = p.real, p.imag
            x -= ox
            y -= oy
            x_new = x * cos_a - y * sin_a + ox
            y_new = x * sin_a + y * cos_a + oy
            return complex(x_new, y_new)

        for path in self.paths:
            for segment in path:
                segment.start = rotate_point(segment.start)
                segment.end = rotate_point(segment.end)
                if hasattr(segment, "control1"):
                    segment.control1 = rotate_point(segment.control1)
                if hasattr(segment, "control2"):
                    segment.control2 = rotate_point(segment.control2)

        dim = self.update()  # rebuild svg_xml after rotation
        return dim

    def bounding_box(self):
        """
        Compute the bounding box of all paths in self.paths.
        Returns(xmin, ymin, xmax, ymax)
        """
        if not self.paths:
            return None  # or (0,0,0,0) if you prefer

        xs, ys = [], []

        for path in self.paths:
            for seg in path:
                points = [seg.start, seg.end]
                if hasattr(seg, "control1"):
                    points.append(seg.control1)
                if hasattr(seg, "control2"):
                    points.append(seg.control2)
                for p in points:
                    xs.append(p.real)
                    ys.append(p.imag)

        xmin = min(xs)
        xmax = max(xs)
        ymin = min(ys)
        ymax = max(ys)
        self.dim_x = xmax - xmin
        self.dim_y = ymax - ymin
        return xmin, ymin, xmax, ymax

    def add_frame(self, padding=15.0):
        """
        Adds a rectangular frame around all paths with a given padding.
        : param padding: distance in same units as SVG coordinates(e.g., mm)
        """
        if not self.paths:
            return
        self.frame = True
        bbox = self.bounding_box()
        if not bbox:
            return  # nothing to frame

        xmin, ymin, xmax, ymax = bbox

        # expand bbox by padding
        xmin -= padding
        ymin -= padding
        xmax += padding
        ymax += padding

        # create the rectangle as a Path (4 sides)
        frame_path = Path(
            Line(complex(xmin, ymin), complex(xmax, ymin)),
            Line(complex(xmax, ymin), complex(xmax, ymax)),
            Line(complex(xmax, ymax), complex(xmin, ymax)),
            Line(complex(xmin, ymax), complex(xmin, ymin)),
        )

        # optionally, add an attribute for stroke
        frame_attr = {"stroke": "red", "fill": "none", "stroke-width": "0.1"}

        # add to your lists
        self.paths.append(frame_path)
        self.attributes.append(frame_attr)

        # update the SVG XML
        dim = self.update()
        return dim

    def remove_frame(self):
        """
        Remove the last path if it is a frame(added by add_frame).
        Assumes the frame was added last.
        """
        if not self.paths:
            return
        self.frame = False
        # Optionally, check if last path is a rectangle
        last_path = self.paths[-1]
        if len(last_path) == 4:  # rectangle has 4 segments
            # remove path and attributes
            self.paths.pop()
            self.attributes.pop()
        dim = self.update()  # rebuild svg_xml
        return dim

    def frame_toggle(self, dist: float):
        if not self.paths:
            return
        if self.frame:
            self.remove_frame()
            self.frame = False
        else:
            self.add_frame(padding=dist)
            self.frame = True



stop_thread = False

def send_hpgl_thread(port, baudrate, data, chunk_size=1024, write_timeout=5):
    global stop_thread
    try:
        # timeout=None for read; finite write timeout to avoid hanging
        with serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=None,           # read timeout
            write_timeout=write_timeout,  # write timeout in seconds
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        ) as ser:
            # short wait for plotter wake-up
            time.sleep(2)
            print("Sending HPGL...")
            
            for i in range(0, len(data), chunk_size):
                if stop_thread:
                    print("Send cancelled.")
                    break
                chunk = data[i:i+chunk_size].encode("ascii")
                try:
                    ser.write(chunk)
                except serial.SerialTimeoutException:
                    print("Write timeout, stopping send.")
                    break
            # ensure all data is sent
            try:
                ser.flush()
            except serial.SerialException:
                pass
            print("Done sending HPGL.")
    except serial.SerialException as e:
        print(f"Error opening serial port {port}: {e}")

# def send_hpgl_tread(port, baudrate, data):
#     try:
#         # timeout ensures serial open won't block forever
#         with serial.Serial(
#             port=port,
#             baudrate=baudrate,
#             bytesize=serial.EIGHTBITS,
#             parity=serial.PARITY_NONE,
#             stopbits=serial.STOPBITS_ONE,
#             timeout=None,  # read timeout
#             write_timeout=None,  # write timeout
#             xonxoff=False,
#             rtscts=False,
#             dsrdtr=False,
#         ) as ser:
#             # optional: poll until the device responds instead of fixed sleep
#             time.sleep(2)  # short wait for plotter wake-up
#             print("Sending HPGL...")
#             ser.write(data.encode("ascii"))
#             time.sleep(0.5)
#             ser.flush()
#             print("Done.")
#     except serial.SerialException as e:
#         print(f"Error opening serial port {port}: {e}")


def send_hpgl(port, baudrate, data):
    thread = threading.Thread(target=send_hpgl_tread, args=(port, baudrate, data))
    thread.start()


def distance(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.hypot(dx, dy)


def lerp(p1, p2, t):
    return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))


# **************************************************
# Flatten cubic Bezier from svgpathtools CubicBezier
# **************************************************


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


# *****************************
# Flatten Line
# *****************************


def flatten_line(
    p0,
    p1,
):
    return [p0, p1]


# ********************************************
# Flatten Quadratic Bezier (from svgpathtools)
# ********************************************


def flatten_quadratic_bezier(p0, p1, p2, max_chord=0.05, min_depth=5):
    # Convert to cubic: P0,P1,P2 → P0,P01,P12,P2
    c1 = (p0[0] + 2 / 3 * (p1[0] - p0[0]), p0[1] + 2 / 3 * (p1[1] - p0[1]))
    c2 = (p2[0] + 2 / 3 * (p1[0] - p2[0]), p2[1] + 2 / 3 * (p1[1] - p2[1]))
    return flatten_cubic_bezier(
        p0, c1, c2, p2, max_chord=max_chord, min_depth=min_depth
    )


# *****************************
# Flatten SVG Path
# *****************************


def flatten_svg_path(path, max_chord=0.05, min_depth=5):
    """
    Flatten an SVG path into a homogeneous list of points with pen up/down flags.
    Returns a list of tuples: (pen, x, y), where 0 = PU, 1 = PD.
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


# *****************************
# Generate HP-GL commands
# *****************************


def generate_hpgl_from_points(points, scale=2):
    """
    Generate HPGL commands from points.
    points: list of(pen, x, y) tuples, 0 = PU, 1 = PD
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
    """Return the angle ( in degrees) at p2 formed by p1-p2-p3"""
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
    points: list of(pen, x, y)
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


def send_to_plotter(attr: object, gfx: object, scale):
    """
    sends the data to the plotter
    """
    # parse the svg file
    paths = gfx.paths
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
    final_scale = scale * attr.scale
    hpgl_cmds = build_header(attr)
    hpgl_cmds += "\n".join(
        generate_hpgl_from_points(
            normalized_points,
            # scale=attr.scale,
            scale=final_scale,
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


if __name__ == "__main__":
    pass
