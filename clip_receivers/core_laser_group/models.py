import ctypes
from models import LaserPoint
from .optimizer import _calculate_current_value


class LaserObject():
    # every interface implementation must provide these attributes:
    # - point_list
    # - clip
    
    # Update clip for all points in point list aswell
    def update_clip(self, clip):
        self.clip = clip
        for laser_point in self.point_list:
            laser_point.clip = self.clip

    # Update anything regarding current time in timeline
    def update(self, clip, current_timeline_time):
        pass

    def __str__(self):
        return('LaserObject, type: ' + str(type(self)))


class StaticLine(LaserObject):
    def __init__(self, from_point, to_point):
        self.point_list = []
        self.point_list.append(from_point)
        self.point_list.append(to_point)

    
class StaticCircle(LaserObject):
    def __init__(self, center_x, center_y, radius, r, g, b):
        import math

        self.point_list = []

        # the lower this value the higher quality the circle is with more points generated
        step_size = 0.1

        # generated vertices
        points_count = int(2 * math.pi / step_size) + 1
        
        # calculate points
        t = 0
        i = 0
        first_x = int(round(radius * math.cos(0) + center_x, 0))
        first_y = int(round(radius * math.sin(0) + center_y, 0))
        while t < 2 * math.pi:
            laser_point = LaserPoint(int(round(radius * math.cos(t) + center_x, 0)), int(round(radius * math.sin(t) + center_y, 0)))
            laser_point.set_color(r, g, b)
            self.point_list.append(laser_point)
            t += step_size
            i += 1


class StaticWave(LaserObject):
    def __init__(self, width, height, r, g, b):
        import math

        # Set up wave properties
        self.wave_length = width
        self.amplitude = 500
        self.frequency = 3
        self.vertical_shift = height / 2

        self.point_list = []
        for x in range(0, width, 50):
            y = math.sin((2 * math.pi * self.frequency * x) / self.wave_length) * self.amplitude + self.vertical_shift
            laser_point = LaserPoint(int(x), int(y))
            laser_point.set_color(r, g, b)
            self.point_list.append(laser_point)


class MovingWave(LaserObject):
    def __init__(self, width, height, r, g, b):
        import math

        # Set up wave properties
        self.wave_length = width
        self.amplitude = 500
        self.frequency = 3
        self.vertical_shift = height / 2

        # Initialize the point list as an empty list
        self.point_list = []

    def update(self, clip, time):
        import math

        clip_duration = clip.end - clip.begin
        self.amplitude = _calculate_current_value(time, clip_duration, clip.transformations['amplitude'])
        self.frequency = _calculate_current_value(time, clip_duration, clip.transformations['frequency'])

        # Clear the point list
        self.point_list = []

        # Add points to the point list
        for x in range(0, self.wave_length, 50):
            # Update the y value based on the current time
            y = math.sin((2 * math.pi * self.frequency * (x + time)) / self.wave_length) * self.amplitude + self.vertical_shift

            # Create a new laser point at this position
            laser_point = LaserPoint(int(x), int(y))

            # Set the color of the laser point
            laser_point.set_color(0, 0, 100)

            # Add the laser point to the point list
            self.point_list.append(laser_point)


class StaticSVG(LaserObject):

    def __init__(self, width, height, r, g, b):
        self.point_list = []
        self.width = width
        self.height = height
        self.r = r
        self.g = g
        self.b = b

    def _extract_points_from_svg(self, file_name):
        from svgpathtools import svg2paths

        paths, _ = svg2paths('clip_receivers/core_laser_group/media/' + file_name)
        points = []

        # When using text: 1 path = 1 character (using Inkscape -> 'Text -> Path')
        for path in paths:
            for line in path:
                start = line.start
                end = line.end

                # otherwise characters will get connected by a line
                blank_point = LaserPoint( int(start.real), int(start.imag))
                blank_point.set_blank()
                points.append(blank_point)

                laser_point_start = LaserPoint( int(start.real), int(start.imag))
                laser_point_start.set_color(self.r, self.g, self.b)
                points.append(laser_point_start)

                laser_point_end = LaserPoint( int(end.real), int(end.imag))
                laser_point_end.set_color(self.r, self.g, self.b)
                points.append(laser_point_end)

        return points

    def _scale_points(self, points):
        min_x = min(point.x for point in points)
        max_x = max(point.x for point in points)
        min_y = min(point.y for point in points)
        max_y = max(point.y for point in points)
        
        scale_x = self.width / (max_x - min_x)
        scale_y = self.height / (max_y - min_y)

        for point in points:
            point.x = int(scale_x * (point.x - min_x))
            point.y = int(scale_y * (point.y - min_y))
        
        return points

    def update(self, clip, current_timeline_time):
        path = clip.clip_parameters['path']
        point_list_from_svg = self._extract_points_from_svg(path)
        scaled_point_list_from_svg = self._scale_points(point_list_from_svg)

        self.point_list = scaled_point_list_from_svg