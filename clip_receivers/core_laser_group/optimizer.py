import configparser
import logging
import numpy
import math
import cProfile


def _calculate_current_value(elapsed_time, duration, transformations):
    percent = (elapsed_time / duration) * 100
    axis_values = list(transformations.values())
    axis_times = list(map(int, transformations.keys()))
    if percent <= axis_times[0]:
        return axis_values[0]
    elif percent >= axis_times[-1]:
        return axis_values[-1]
    else:
        for i in range(len(axis_times) - 1):
            if percent >= axis_times[i] and percent <= axis_times[i+1]:
                t1 = axis_times[i]
                t2 = axis_times[i+1]
                v1 = axis_values[i]
                v2 = axis_values[i+1]
                return v1 + (v2-v1) * (percent-t1) / (t2-t1)

def _euclidean_distance(x1, y1, x2, y2):
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5

def _find_center(points):
    x_coords = [p.x for p in points]
    y_coords = [p.y for p in points]
    center_x = sum(x_coords) / len(x_coords)
    center_y = sum(y_coords) / len(y_coords)
    return (center_x, center_y)

# return point list, but with:
# - blank points (so laser objects will not become connected by a line)
# - transformatioms
#
# Better ideas:
#   - https://www.art-science.org/journal/v7n4/v7n4pp155/artsci-v7n4pp155.pdf 
#   - https://www.jstage.jst.go.jp/article/tsjc/2008/0/2008_0_1/_pdf
def _get_optimized_point_list(visible_laser_objects, receiver_parameters, current_timeline_time):
    from .models import LaserPoint
    from copy import copy
    import numpy

    optimized_point_list = []

    # Iterate over all basic shapes like line, circle, wave,...
    for visible_laser_object in visible_laser_objects:

        clip = visible_laser_object.clip

        visible_laser_object.update_clip(clip)

        # calculate transformations data
        if clip.transformations:
            current_clip_time = current_timeline_time - clip.begin
            clip_duration = clip.end - clip.begin
            clip_time_percentage = round((current_clip_time % clip_duration) / clip_duration * 100, 2)

        # Some LaserObjects need to update themselves due to current time (moving waves, moving SVG images...)
        visible_laser_object.update(clip, current_timeline_time)

        # add a blank points
        # to make objects not become connected
        if optimized_point_list:
            last_point = optimized_point_list[-1]
            distance = _euclidean_distance(last_point.x, last_point.y, visible_laser_object.point_list[0].x, visible_laser_object.point_list[0].y)
            blank_points_needed = max(1, int(distance * receiver_parameters['blank_point_frames'] / receiver_parameters['width']))
        else:
            blank_points_needed = receiver_parameters['blank_point_frames']

        for _ in range(blank_points_needed):
            blank_laser_point1 = LaserPoint(visible_laser_object.point_list[0].x, visible_laser_object.point_list[0].y)
            blank_laser_point1.set_color(0, 0, 0)
            blank_laser_point1.clip = clip
            optimized_point_list.append(blank_laser_point1)

        # add interpolated points
        # to have sharper line ends
        laser_object_points = len(visible_laser_object.point_list)
                
        previously_optimized_laser_point = None
        for laser_point in visible_laser_object.point_list:
            optimized_laser_point = copy(laser_point)
            optimized_laser_point.clip = clip

            if previously_optimized_laser_point:
                distance = _euclidean_distance(previously_optimized_laser_point.x, previously_optimized_laser_point.y, optimized_laser_point.x, optimized_laser_point.y)
                interpolated_points_needed = max(2, int(distance * receiver_parameters['interpolated_points'] / receiver_parameters['width']))
                interpolated_x_coords = numpy.linspace(previously_optimized_laser_point.x, optimized_laser_point.x, num=interpolated_points_needed)
                interpolated_y_coords = numpy.linspace(previously_optimized_laser_point.y, optimized_laser_point.y, num=interpolated_points_needed)

                i = 0
                for interpolated_x_coord in interpolated_x_coords:
                    interpolated_optimized_laser_point = copy(optimized_laser_point)
                    interpolated_optimized_laser_point.x = interpolated_x_coords[i]
                    interpolated_optimized_laser_point.y = interpolated_y_coords[i]
                    optimized_point_list.append(interpolated_optimized_laser_point)
                    i += 1

            else:
                optimized_point_list.append(optimized_laser_point)

            previously_optimized_laser_point = optimized_laser_point
            
        # add blank point at end of laser object
        blank_laser_point2 = LaserPoint(visible_laser_object.point_list[0].x, visible_laser_object.point_list[0].y)
        blank_laser_point2.set_color(0, 0, 0)
        blank_laser_point2.clip = clip
        optimized_point_list.append(blank_laser_point2)

        # add transformations
        if clip.transformations:
            
            # Calculate the center of the current laser object
            laser_object_points = [point for point in optimized_point_list if point.clip.id == clip.id]
            laser_object_center = _find_center(laser_object_points)

            laser_points_in_clip = 0
            i = 1
            for optimized_point in optimized_point_list:
                if optimized_point.clip.id == clip.id:
                    laser_points_in_clip += 1

                    # color
                    for color in ['r', 'g', 'b']:
                        if color in clip.transformations:
                            if not optimized_point.is_blank():
                                setattr(optimized_point, color, 255/100 *_calculate_current_value(current_clip_time, clip_duration, clip.transformations[color]))

                    # scale (size)
                    if "s" in clip.transformations:
                        scale_factor = 10/100 * _calculate_current_value(current_clip_time, clip_duration, clip.transformations['s'])
                        # Scale the points relative to the center
                        optimized_point.x = laser_object_center[0] + (optimized_point.x - laser_object_center[0]) * scale_factor
                        optimized_point.y = laser_object_center[1] + (optimized_point.y - laser_object_center[1]) * scale_factor

                    # rotation
                    if "rotate" in clip.transformations:
                        rotation_angle = math.radians(_calculate_current_value(current_clip_time, clip_duration, clip.transformations['rotate']))
                        # Rotate the points relative to the center
                        cos_val = math.cos(rotation_angle)
                        sin_val = math.sin(rotation_angle)
                        dx = optimized_point.x - laser_object_center[0]
                        dy = optimized_point.y - laser_object_center[1]
                        optimized_point.x = cos_val * dx - sin_val * dy + laser_object_center[0]
                        optimized_point.y = sin_val * dx + cos_val * dy + laser_object_center[1]

                    if "dots" in clip.transformations:
                        dots_value = _calculate_current_value(current_clip_time, clip_duration, clip.transformations['dots'])
                        #print(dots_value)
                        if i % dots_value:
                            optimized_point.set_blank()

                    # position
                    if "x" in clip.transformations:
                        optimized_point.x += receiver_parameters['width']/100 * _calculate_current_value(current_clip_time, clip_duration, clip.transformations['x'])
                    if "y" in clip.transformations:
                        optimized_point.y += receiver_parameters['height']/100 *_calculate_current_value(current_clip_time, clip_duration, clip.transformations['y'])

                    i += 1


        # remove laser points out of screen coordinates
        for optimized_point in optimized_point_list:
                if optimized_point.y >= receiver_parameters['height'] or optimized_point.y <= 0 or optimized_point.x >= receiver_parameters['width'] or optimized_point.x <= 0:
                    optimized_point.set_blank()

                    # limit y
                    if optimized_point.y > receiver_parameters['height']:
                        optimized_point.y = receiver_parameters['height']
                    elif optimized_point.y < 0:
                        optimized_point.y = 0

                    # limit x
                    if optimized_point.x > receiver_parameters['width']:
                        optimized_point.x = receiver_parameters['width']
                    elif optimized_point.x <= 0:
                        optimized_point.x = 0

    return optimized_point_list
