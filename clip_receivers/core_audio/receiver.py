from models import ReceiverModel
import pygame
from config import config as config


class Receiver(ReceiverModel):

    def __init__(self, id, title, type, receiver_parameters, shared_dict):
        super().__init__(id, title, type, receiver_parameters, shared_dict)

        self.shared_dict = shared_dict
        
        pygame.mixer.init()
        print('[Receiver] ' + self.id + ": Loading path: " + str(self.receiver_parameters['path']))
        
        pygame.mixer.music.load('clip_receivers/core_audio/media/' + self.receiver_parameters['path'])
        pygame.mixer.music.set_volume(receiver_parameters['volume'])
        pygame.mixer.music.play()
        position = self.shared_dict['time']/1000
        print('[Receiver] Seeking to seconds: ' + str(position))
        pygame.mixer.music.set_pos(position)
        pygame.mixer.music.pause()
        
    def play(self, clip):
        super().play(clip)
        print('[Receiver] ' + self.id + ": Playing loaded path")
        pygame.mixer.music.unpause()
        
    def stop(self, clip_id):
        position = config['timeline']['position']
        print('[Receiver] Seeking to seconds: ' + str(position))
        pygame.mixer.music.set_pos(position/1000)
        pygame.mixer.music.pause()
