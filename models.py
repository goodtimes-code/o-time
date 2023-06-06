import redis
import time
import json
from intervaltree import Interval, IntervalTree
from datetime import datetime
from collections import namedtuple
from config import config as config
import pygame as pg
from copy import copy


class Timeline(IntervalTree):
    pass
    

class Clip():
    begin = None
    end = None
    title = None
    type = None
    
    clip_parameters = {}

    played = False
    stopped = False

    transformations = []
    
    clips = []

    def __init__(self, clip_data):
        from main import config

        self.id = clip_data['id']
        self.begin = clip_data['begin']
        self.end = clip_data['end']
        self.title = clip_data['title']
        self.type = clip_data['type']
        self.receiver = clip_data['receiver']
        self.clip_parameters = clip_data['clip_parameters']
        self.transformations = clip_data['transformations']

        self.r = redis.StrictRedis(host=config['server']['host'], password=config['server']['password'],port=config['server']['port'], db=0)
        
    def play(self):
        message = {
            'receiver': self.receiver,
            'action': 'play',
            'clip': json.dumps(self, default=lambda obj: obj.to_dict())
        }
        self.r.publish("message_queue", json.dumps(message))
        self.played = True

    def stop(self):
        self.stopped = True
        message = {
            'receiver': self.receiver,
            'action': 'stop',
            'clip_id': self.id
        }
        self.r.publish("message_queue", json.dumps(message))
        self.stopped = True

    def __str__(self):
        return self.title

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'type': self.type,
            'receiver': self.receiver,
            'begin': self.begin,
            'end': self.end,
            'clip_parameters': self.clip_parameters,
            'transformations': self.transformations
        }


class ReceiverModel():
    parameters = None

    def __init__(self, id, title, type, receiver_parameters, shared_dict):
        from main import config

        self.shared_dict = shared_dict

        self.id = id
        self.title = title
        self.type = type
        self.receiver_parameters = receiver_parameters

        self.r = redis.StrictRedis(host=config['server']['host'], password=config['server']['password'],port=config['server']['port'], db=0)

        print('[ReceiverModel] ' + self.id + ': initialized.')

    def clip_from_dict(self, clip_data):
        clip = Clip(clip_data)
        return clip

    def receive(self):
        while self.shared_dict['running']:
            
            pubsub = self.r.pubsub()
            pubsub.subscribe("message_queue")
            for raw_message in pubsub.listen():
                if raw_message["type"] == "message":
                    message = json.loads(raw_message['data'])
                    if 'start_time' in message:
                        self.shared_dict['time'] = message['start_time']
                    elif message['receiver'] == self.id and message['action'] == 'play':
                        clip = self.clip_from_dict(json.loads(message['clip']))
                        self.play(clip)
                    elif message['receiver'] == self.id and message['action'] == 'stop':
                        self.stop(message['clip_id'])

    def play(self, clip):
        print('[ReceiverModel] ' + self.id + ': play(' + clip.id + ')')

    def stop(self, clip_id):
        print('[ReceiverModel] ' + self.id + ': stop(' + clip_id + ')')


class LaserPoint():
    def __init__(self, x, y, r=0, g=0, b=0, clip=None):
        self.x = x
        self.y = y
        self.r = int(round(r))
        self.g = int(round(g))
        self.b = int(round(b))
        self.clip = None

    def set_color(self, r, g, b):
        self.r = int(round(r))
        self.g = int(round(g))
        self.b = int(round(b))

    def is_blank(self):
        if self.r == 0 and self.g == 0 and self.b == 0:
            return True
        else:
            return False

    def set_blank(self):
        self.r = 0
        self.g = 0
        self.b = 0

    def __str__(self):
        return ('X:' + str(self.x) + ', Y:' + str(self.y) + ', R:' + str(self.r) + ', G:' + str(self.g) + ', B:' + str(self.b) + ', Blank: ' + str(self.is_blank()))


class LaserPreview():
    def __init__(self, shared_dict):
        self.shared_dict = shared_dict

    def main(self):
        self.LASER_POINT_SIZE = int(config['laser_preview']['laser_point_size'])
        print('[LaserPreview] Initialized')

        pg.init()
        pg.display.set_caption('Laser preview')

        self.screen = pg.display.set_mode(
            (int(config['laser_preview']['width']) * float(config['laser_preview']['screen_scale_factor']), 
            int(config['laser_preview']['height']) * float(config['laser_preview']['screen_scale_factor'])), 
            pg.HWSURFACE
        )
        self.screen_rect = self.screen.get_rect()
        self.clock = pg.time.Clock()
        self.font = pg.font.Font(None, 24)

        self.r = redis.StrictRedis(host=config['server']['host'], password=config['server']['password'],port=config['server']['port'], db=0)

        while self.shared_dict['running']:
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.shared_dict['running'] = False
                    pg.quit()
                    print('[LaserPreview] Successfully stopped')
                elif event.type == pg.KEYDOWN and event.key == pg.key.key_code('P'):
                    print('[LaserPreview] Start timeline playback')
                    message = {
                        'receiver': 'timeline_playback_controller',
                        'action': 'play'
                    }
                    self.r.publish("message_queue", json.dumps(message))
            
            self.update_screen()
            time.sleep(config['laser_preview']['screen_update_sleep'])

    def draw_text(self, text, position):
        surface = self.font.render(text, True, (255, 255, 255))
        self.screen.blit(surface, position)

    def update_screen(self):
        try:
            optimized_point_list_str = self.r.get(config['laser_preview']['group_id'] + "_optimized_point_list")
        except Exception as e:
            print(e)
            optimized_point_list_str = None
            print("Waiting for data...")

        if optimized_point_list_str:
                optimized_point_list = [LaserPoint(**point_data) for point_data in json.loads(optimized_point_list_str)]
        else:
            print("Waiting for data...")
            optimized_point_list = []
        
        if self.shared_dict['running']:
            self.screen.fill('black') # clear screen
            self.draw_text(f"Time: {self.shared_dict['time']/1000}", (10, self.screen.get_height() - 30))  # Draw the time
        else:
            return

        previous_laser_point_output = None
        for laser_point in optimized_point_list:
            laser_point_output = copy(laser_point)
            laser_point_output.x = laser_point_output.x * float(config['laser_preview']['screen_scale_factor'])
            laser_point_output.y = laser_point_output.y * float(config['laser_preview']['screen_scale_factor'])  

            # draw laser point
            if not laser_point.is_blank():
                pg.draw.circle(self.screen, (laser_point_output.r, laser_point_output.g, laser_point_output.b) , (laser_point_output.x, laser_point_output.y), self.LASER_POINT_SIZE)
                
            # connect laser points with line
            #if previous_laser_point_output and not laser_point.is_blank():
            #    pg.draw.line(self.screen, (laser_point_output.r, laser_point_output.g, laser_point_output.b, 0), (previous_laser_point_output.x, previous_laser_point_output.y), (laser_point_output.x, laser_point_output.y), self.LASER_POINT_SIZE)
            
            previous_laser_point_output = laser_point_output

        pg.display.flip() # show all drawings


class TimelinePlaybackController:
    def __init__(self, shared_dict):
        self.r = redis.StrictRedis(host=config['server']['host'], password=config['server']['password'],port=config['server']['port'], db=0)

        self.shared_dict = shared_dict

    def stop_earlier_clips(self, timeline, time):
        earlier_intervals = sorted(timeline[0:time-1])
        for interval in earlier_intervals:
            clip = interval.data
            if time > clip.end and not clip.stopped:
                print('[Main] Stopping clip: ' + str(clip.title) + ' (ID: ' + str(clip.id) + ')')
                clip.stop()

    def stop_all_clips(self, timeline):
        earlier_intervals = sorted(timeline[0:timeline.end()])
        for interval in earlier_intervals:
            clip = interval.data
            print('[Main] Stopping clip: ' + str(clip.title) + ' (ID: ' + str(clip.id) + ')')
            clip.stop()

    def receive(self):
        while self.shared_dict['running']:
            pubsub = self.r.pubsub()
            pubsub.subscribe("message_queue")
            for raw_message in pubsub.listen():
                if raw_message["type"] == "message":
                    message = json.loads(raw_message['data'])
                    if message['receiver'] == 'timeline_playback_controller' and message['action'] == 'play':
                        self.play()

    def play(self):
        from main import config
        import time as time_lib

        self.shared_dict['time'] = config['timeline']['position']
        self.shared_dict['start_time'] = time_lib.perf_counter()

        # Read clips from timeline
        t = Timeline()
        for clip_data in config['clips']:
            clip = Clip(clip_data)
            t[clip.begin:clip.end] = clip

        while self.shared_dict['running']:
            elapsed_time = time.perf_counter() - self.shared_dict['start_time']
            self.shared_dict['time'] = int(elapsed_time * 1000) + config['timeline']['position']

            # Play clips, scheduled for current time
            intervals = sorted(t[self.shared_dict['time']])
            for interval in intervals:
                clip = interval.data

                if not clip.played:
                    print('[Main] Playing clip: ' + str(clip.title) + ' (ID: ' + str(clip.id) + ')')
                    clip.play() 

            self.stop_earlier_clips(t, self.shared_dict['time'])

            #time.sleep(0.01)

            if self.shared_dict['time'] > t.end():
                print('[Main] Last clip was played. Finishing.')
                self.stop_all_clips(t)
                break