import ctypes
import threading
import time
from copy import copy
import json

from models import ReceiverModel, Clip, LaserPoint
from .models import HeliosPoint
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

        self.init_helios_dac()

        self.r = redis.StrictRedis(host=config['server']['host'], password=config['server']['password'],port=config['server']['port'], db=0)

        laser_output_thread = threading.Thread(target=self.laser_output, daemon=True)
        laser_output_thread.name = self.id + ' (laser output)'
        laser_output_thread.start()
        
        print('[Receiver] ' + self.id + ': Initialized')

    def init_helios_dac(self):
        global HeliosLib
        HeliosLib = ctypes.cdll.LoadLibrary("clip_receivers/core_laser_helios/libHeliosDacAPI.so")
        numDevices = HeliosLib.OpenDevices()
        print('[Receiver] ' + self.id + ': Found ' + str(numDevices) + ' Helios DACs')

    def wait_until_ready(self):
        statusAttempts = 0
        max_status_attempts = 512
        while (statusAttempts < max_status_attempts and HeliosLib.GetStatus(0) != 1):
                statusAttempts += 1

    def blackout(self):
        point_type = HeliosPoint * 1
        helios_points = point_type()
        helios_points[0] = HeliosPoint(0, 0, 0, 0, 0, 0)
        HeliosLib.WriteFrame(0, self.receiver_parameters['scan_rate'], 0, ctypes.pointer(helios_points), 1)

    # Thread: Iterate over optimized visible laser objects and write to Helios DAC
    def laser_output(self):
        print('[Receiver] ' + self.id + ': Laser output thread started')

        while self.shared_dict['running']:
            optimized_point_list_str = self.r.get(self.receiver_parameters['group_id'] + "_optimized_point_list")

            if optimized_point_list_str:
                    optimized_point_list = [LaserPoint(**point_data) for point_data in json.loads(optimized_point_list_str)]
            else:
                print("Waiting for data...")
                optimized_point_list = []
            
            # Create a new list with clip references removed
            optimized_point_list_no_clip = []
            for point in optimized_point_list:
                point_dict = point.__dict__.copy()
                point_dict['clip'] = None
                optimized_point_list_no_clip.append(point_dict)

            count_points = len(optimized_point_list)
            if count_points > 0:
                helios_point_type = HeliosPoint * count_points
                helios_points = helios_point_type()

                i = 0
                for laser_point in optimized_point_list:
                    helios_points[i] = HeliosPoint(int(laser_point.x), int(laser_point.y), int(laser_point.r * self.receiver_parameters['intensity_factor']), int(laser_point.g * self.receiver_parameters['intensity_factor']), int(laser_point.b * self.receiver_parameters['intensity_factor']), 0)
                    i += 1

                self.wait_until_ready()

                # really draw points via Helios Laser DAC
                HeliosLib.WriteFrame(0, self.receiver_parameters['scan_rate'], 0, ctypes.pointer(helios_points), count_points)
            else:
                self.wait_until_ready()
                self.blackout()