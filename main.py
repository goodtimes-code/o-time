import json
import time as time_lib
from playsound import playsound
import importlib
import threading
from models import Timeline, Clip, LaserPreview, TimelinePlaybackController
import redis
from multiprocessing import Manager
import cProfile


# Init show from file
file = open('config.json')
config = json.load(file)

def stop_earlier_clips(timeline, time):
    earlier_intervals = sorted(timeline[0:time-1])
    for interval in earlier_intervals:
        clip = interval.data
        if time > clip.end and not clip.stopped:
            print('[Main] Stopping clip: ' + str(clip.title) + ' (ID: ' + str(clip.id) + ')')
            clip.stop()

def stop_all_clips(timeline):
    earlier_intervals = sorted(timeline[0:timeline.end()])
    for interval in earlier_intervals:
        clip = interval.data
        print('[Main] Stopping clip: ' + str(clip.title) + ' (ID: ' + str(clip.id) + ')')
        clip.stop()

def main():
    # Initialize shared variables using multiprocessing.Value
    manager = Manager()
    shared_dict = manager.dict()
    shared_dict['start_time'] = time_lib.perf_counter()
    shared_dict['time'] = config['timeline']['position']
    shared_dict['running'] = True

    # Connect to server
    r = redis.StrictRedis(host=config['server']['host'], password=config['server']['password'],port=config['server']['port'], db=0)

    # Start one thread per receiver
    for receiver_data in config['receivers']:
        receiver_class = getattr(__import__("clip_receivers." + receiver_data['type']+".receiver", fromlist=["Receiver"]), "Receiver")
        receiver = receiver_class(receiver_data['id'], receiver_data['title'], receiver_data['type'], receiver_data['receiver_parameters'], shared_dict)
        receiver_thread = threading.Thread(target=receiver.receive, daemon=True)
        receiver_thread.name = receiver_data['id']
        receiver_thread.start()
        #cProfile.run('receiver_thread.start()')
        print('[Main] Receiver started: ' + str(receiver.id))

    # Timeline playback controller
    timeline_playback_controller = TimelinePlaybackController(shared_dict)
    timeline_playback_controller_thread = threading.Thread(target=timeline_playback_controller.receive, daemon=True)
    timeline_playback_controller_thread.start()

    # Laser preview UI
    laser_preview = LaserPreview(shared_dict)
    laser_preview.main()


if __name__ == '__main__':
    main()
    #cProfile.run('main()')
