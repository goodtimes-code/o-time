import ctypes
import threading
import time
from copy import copy
import json

from models import ReceiverModel, Clip, LaserPoint
from .optimizer import _get_optimized_point_list
from .models import StaticLine, StaticCircle, StaticWave, MovingWave, StaticSVG
import redis
from config import config as config

"""
Structure:

main:
    1 Timeline 
        n Clips
            1 Clip 
                1 LaserObject

"""

class Receiver(ReceiverModel):

    def __init__(self, id, title, type, receiver_parameters, shared_dict):
        super().__init__(id, title, type, receiver_parameters, shared_dict)

        self.shared_dict = shared_dict

        self.prepare_laser_objects()

        self.visible_laser_objects = []

        self.r = redis.StrictRedis(host=config['server']['host'], password=config['server']['password'],port=config['server']['port'], db=0)

        laser_output_thread = threading.Thread(target=self.laser_output, daemon=True)
        laser_output_thread.name = self.id + ' (laser output)'
        laser_output_thread.start()
        
        print('[Receiver] ' + self.id + ': Initialized')

    def prepare_laser_objects(self):
        laser_point1 = LaserPoint(0, self.receiver_parameters['height']/2)
        laser_point1.set_color(0, 255, 0)

        laser_point2 = LaserPoint(self.receiver_parameters['width'], self.receiver_parameters['height']/2)
        laser_point2.set_color(0, 255, 0)

        laser_point3 = LaserPoint(self.receiver_parameters['width']/2, 0)
        laser_point3.set_color(255, 0, 0)

        laser_point4 = LaserPoint(self.receiver_parameters['width']/2, self.receiver_parameters['height'])
        laser_point4.set_color(255, 0, 0)

        self.LASEROBJECT_MAPPING = (
            (0, StaticLine(laser_point1, laser_point2)), # Green horizontal line
            (1, StaticLine(laser_point3, laser_point4)), # Red vertical line
            (2, StaticWave(self.receiver_parameters['width'], self.receiver_parameters['height'], 0, 0, 255)), # Blue static wave
            (3, StaticCircle(self.receiver_parameters['width']/2, self.receiver_parameters['height']/2, 500, 0, 0, 255)), # Blue static circle
            (4, MovingWave(self.receiver_parameters['width'], self.receiver_parameters['height'], 0, 0, 255)), # Blue moving wave
            (5, StaticSVG(self.receiver_parameters['width'], self.receiver_parameters['height'], 0, 255, 0)), # Blank SVG (set SVG path via clip parameter)
        )

    def play(self, clip):
        #start_time = time.time()
        
        super().play(clip)

        print('[Receiver] ' + self.id + ': Playing clip ' + clip.id + '...')
        
        laser_object = copy(self.LASEROBJECT_MAPPING[clip.clip_parameters['laser_object']][1])
        
        laser_object.clip = clip

        self.visible_laser_objects.append(laser_object)

    def stop(self, clip_id):
        super().stop(clip_id)
        print('[Receiver] ' + self.id + ': Stopping clip ' + clip_id + '...')

        # create new list, but without laser objects having this clip ID
        self.visible_laser_objects = [visible_laser_object for visible_laser_object in self.visible_laser_objects if visible_laser_object.clip.id != clip_id]

    # Thread: Iterate over optimized visible laser objects and send output via Redis
    def laser_output(self):
        print('[Receiver] ' + self.id + ': Laser output thread started')

        while self.shared_dict['running']:
            optimized_point_list = _get_optimized_point_list(self.visible_laser_objects, self.receiver_parameters, self.shared_dict['time'])
            
            # Create a new list with clip references removed
            optimized_point_list_no_clip = []
            for point in optimized_point_list:
                point_dict = point.__dict__.copy()
                point_dict['clip'] = None
                optimized_point_list_no_clip.append(point_dict)

            # Serialize the new list
            self.r.set(self.receiver_parameters['group_id'] + "_optimized_point_list", json.dumps(optimized_point_list_no_clip))

            time.sleep(self.receiver_parameters['laser_output_sleep'])

