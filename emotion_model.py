import math
import numpy as np
import threading
import multiprocessing
import time


class EmotionVector:
    # emotion vector represent emotion
    def __init__(self, **kwargs):
        if "strength" in kwargs and "angle" in kwargs:
            # use strength, angle to represent emotion 
            # strength -> [0, 1]
            self.strength = None
            # angle -> [0, 360]
            self.angle = None
            self.set_strength_angle(kwargs["strength"], kwargs["angle"])
        elif "x" in kwargs and "y" in kwargs:
            # use x: valence, y: arousal to represent emotion
            self.x = None
            self.y = None
            self.set_xy(kwargs["x"], kwargs["y"])

    def set_strength_angle(self, strength, angle):
        # from strengh, angle to x, y
        self.strength = strength
        self.angle = angle
        self.x = strength * math.cos(math.radians(angle))
        self.y = strength * math.sin(math.radians(angle))

    def set_xy(self, x, y):
        # from x, y, to calculate strength, angle
        self.x = x
        self.y = y
        self.strength = math.sqrt(math.pow(x, 2)+math.pow(y, 2))
        angle_aux = math.degrees(math.asin(y/self.strength))
        if angle_aux >= 0:
            if x >= 0:
                self.angle = 0 + angle_aux
            else:
                self.angle = 180 - angle_aux
        else:
            if x >= 0:
                self.angle = 360 + angle_aux
            else:
                self.angle = 180 - angle_aux

    def __repr__(self):
        return "({:.2f}, {:.2f}), \n angle: {:.2f}, strength: {:.2f}".format(self.x, self.y, self.angle, self.strength)

    def __add__(self, other):
        new = EmotionVector()
        new.set_xy(self.x + other.x, self.y + other.y)
        return new

    def __sub__(self, other):
        new = EmotionVector()
        new.set_xy(self.x - other.x, self.y - other.y)
        return new


class EmotionSpace:

    mapper = {1: {0: "surprised", 1: "excited", 2: "pleasant", 3: "happy"},
              2: {0: "surprised", 1: "angry", 2: "fear", 3: "annoyed"},
              3: {0: "calm", 1: "tired", 2: "desperate", 3: "sad"},
              4: {0: "calm", 1: "relaxed", 2: "peaceful", 3: "satisfied"}}
    emotions = ["surprised", "excited", "pleasant", "happy",
                "angry", "fear", "annoyed", "clam", "tired",
                "desperate", "sad", "relaxed", "peaceful", "satisfied"]


class Emotion(EmotionVector):
    # emotion transition
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mapper = EmotionSpace.mapper
        self.area = None
        self.decay_thread = None
        self.decay_stop = False

    def get_emotion(self):
        return self.get_area_emo()

    def set_area(self):
        self.area = list(filter(lambda area: (self.angle/360*4) <= area, range(1, 5)))[0]

    def get_area_emo(self, threshold=math.pow(2, 0.5)/2):
        self.set_area()
        x_aux = int(math.fabs(self.x) <= threshold)
        y_aux = int(math.fabs(self.y) <= threshold)
        if math.fabs(self.y) > 0.9:
            x_aux -= 1
        if y_aux:
            y_aux += 1
        return self.mapper[self.area][x_aux + y_aux]

    def change_emotion(self, target, nt, t):
        assert isinstance(target, EmotionVector) or isinstance(target, Emotion)
        delta = target - self
        curr_x, curr_y = np.array([self.x, self.y]) + np.array([delta.x, delta.y]) * t / nt
        curr = Emotion()
        curr.set_xy(curr_x, curr_y)
        return curr
    
    def decay_emotion(self, target, nt=20):
        delta = target - self
        t_change = np.array([delta.x, delta.y]) / nt
        
        t_count = 0
        print(self)
        while not self.decay_stop:
            if t_count >= nt:
                break
            time.sleep(1)
            self.set_xy(self.x+t_change[0], self.y+t_change[1])
            print(self)
            t_count += 1
    
    def start_decay(self, target, nt=20):
        self.decay_thread = threading.Thread(target=self.decay_emotion, args=[target, nt])
        self.decay_thread.start()
    
    def stop_decay(self):
        self.decay_stop = True
        self.decay_thread.join()
#         self.decay_process.join()
        
    def __add__(self, other):
        new = Emotion()
        new.set_xy(self.x + other.x, self.y + other.y)
        return new

    def __sub__(self, other):
        new = Emotion()
        new.set_xy(self.x - other.x, self.y - other.y)
        return new
        
    def __repr__(self):
        return "emotion: {}, ({:.2f}, {:.2f}), \n angle: {:.2f}, strength: {:.2f}".format(
            self.get_emotion(), self.x, self.y, self.angle, self.strength)
    

class Event:
    # variables of an event
    def __init__(self, name, importance, condition, resource, suddeness, event_objects, total_progress, contribution):
        """
        :param name: str
        :param importance: float [-1, 1]
        :param condition: bool
        :param resource_availabel: bool
        :param suddeness: bool
        :param evt_object: EventObjects
        """
        self.name = name
        self.importance = importance
        self.condition = condition
        self.resource_available = resource
        self.suddeness = suddeness
        self.event_objects = event_objects
        self.total_progress = total_progress
        self.contribution = contribution

    def __setattr__(self, key, value):
        self.__dict__[key] = value

    def __getattr__(self, item):
        return self.__dict__[item]


class EventObjects:
    # variables of event objects in an event
    def __init__(self, name, living, familiarity, risk=False, agent_personality=None):
        """
        :param name: str
        :param living: bool
        :param familiarity: float [-1, 1]
        :param risk: bool
        :param agent_personality=None: a instance of class Personality
        """
        self.name = name
        self.living = living
        self.familiarity = familiarity
        self.risk = risk
        self.agent_personality = agent_personality
        self.living_agent_risk()
    
    def living_agent_risk(self):
        # risk of living creature depends on personalities
        if self.living and self.agent_personality:
            if (self.agent_personality.E and self.agent_personality.A and
                self.agent_personality.N is False):
                self.risk = False
            elif (self.agent_personality.E is False and 
                  self.agent_personality.A is False and
                  self.agent_personality.N):
                self.risk = True

    def __setattr__(self, key, value):
        self.__dict__[key] = value

    def __getattr__(self, item):
        return self.__dict__[item]
    
    def __repr__(self):
        return "name: {0}, living_object: {1}, familiar {2}, risk: {3}".format(
            self.name, self.living, self.familiarity, self.risk)


class Personality:
    def __init__(self, O, C, E, A, N):
        """

        :param O: bool positive -> True
        :param C: bool
        :param E: bool
        :param A: bool
        :param N: bool
        """
        self.O = O
        self.C = C
        self.E = E
        self.A = A
        self.N = N

    def __setattr__(self, key, value):
        self.__dict__[key] = value

    def __getattr__(self, item):
        return self.__dict__[item]


class Event2Emotion:
    # emotion generation
    def __init__(self, event, personality):
        super().__init__()
        self.emotions_weight = {emo: 0 for emo in EmotionSpace.emotions}
        self.event = event
        self.personality = personality
        self.default_emotions = self.init_emotions()
        self.emotion = None
        self.mood = (0.25, 0)
        self.current_emotion = self.mood
    
    def init_emotions(self):
        # boundaries of each emotions in the emotional Coordinate System        
        emotion_boundaries = {"happy": {"x": 0.25, "y": 0.25},
        "satisfied": {"x": 0.25, "y": -0.25},
        "annoyed": {"x": -0.25, "y": 0.25},
        "sad": {"x": -0.25, "y": -0.25},
        "excited": {"x": math.sqrt(2)/4, "y": 0.75},
        "relaxed": {"x": math.sqrt(2)/4, "y": -0.75},
        "angry": {"x": -math.sqrt(2)/4, "y": 0.75},
        "tired": {"x": -math.sqrt(2)/4, "y": -0.75},
        "pleasant": {"x": 0.75, "y": math.sqrt(2)/4},
        "peaceful": {"x": 0.75, "y": -math.sqrt(2)/4},
        "fear": {"x": -0.75, "y": math.sqrt(2)/4},
        "desperate": {"x": -0.75, "y": -math.sqrt(2)/4},
        "surprised": {"x": 0, "y": 1},
        "calm": {"x": 0, "y": -1}}
    
        return emotion_boundaries

    def change_emotion_weight(self, emotion, changes):
        # change emotion weights
        self.emotions_weight[emotion] += changes

    def perceive(self):
        # universal emotion generated from variables objectively describe the event
        if self.event.importance > 0:
            w = self.event.importance*10
            if self.event.condition:
                self.change_emotion_weight('happy', w)
            else:
                self.change_emotion_weight('annoyed', w)
        elif self.event.importance < 0:
            w = abs(self.event.importance*10)
            self.change_emotion_weight('annoyed', w)
        else:
            self.change_emotion_weight('annoyed', 2)
        
        if self.event.condition is False:
            if self.event.resource_available:
                self.change_emotion_weight('satisfied', 2.5)
            else:
                self.change_emotion_weight('sad', 2.5)
                self.change_emotion_weight('fear', 2.5)
                self.change_emotion_weight('angry', 2.5)
        
        if self.event.suddeness:
            self.change_emotion_weight('surprised', 10)
        
        if self.event.condition:
            if self.event.event_objects.familiarity > 0:
                w = self.event.event_objects.familiarity*2.5
                self.change_emotion_weight('satisfied', w)
            else:
                w = abs(self.event.event_objects.familiarity*2.5)
                self.change_emotion_weight('excited', w)
        else:
            if self.event.event_objects.familiarity > 0:
                w = self.event.event_objects.familiarity*2.5
                self.change_emotion_weight('angry', w)
            else:
                w = abs(self.event.event_objects.familiarity*2.5)
                self.change_emotion_weight('peaceful', w)

        if self.event.condition:
            if self.event.event_objects.risk:
                self.change_emotion_weight('excited', 5)
                self.change_emotion_weight('happy', 5)
        else:
            if self.event.event_objects.risk:
                self.change_emotion_weight('desperate', 5)
                self.change_emotion_weight('sad', 5)
                
    def apprise(self, context):
        # modify emotion after apprising the event based on personlaity 
        if self.event.event_objects.risk:
            if self.personality.N:
                self.change_emotion_weight('fear', 10)
                self.change_emotion_weight('angry', 10)

            if self.personality.O:
                self.change_emotion_weight('satisfied', 10)
                
        if self.event.importance > 0:
            w = self.event.importance * 10
            if self.event.condition:
                if self.personality.C:
                    self.change_emotion_weight('excited', w)
                if self.personality.N:
                    self.change_emotion_weight('excited', 2*w)
                    self.change_emotion_weight('pleasant', 2*w)
                if self.personality.O:
                    self.change_emotion_weight('excited', w)
                    self.change_emotion_weight('pleasant', w)
                if self.personality.A:
                    self.change_emotion_weight('relaxed', w)
            # failed
            else:
                if self.personality.C:
                    self.change_emotion_weight('annoyed', 2*w)
                if self.personality.N:
                    self.change_emotion_weight('angry', 2*w)
                    self.change_emotion_weight('fear', 2*w)
                if self.personality.O:
                    self.change_emotion_weight('satisfied', w)
                else:
                    self.change_emotion_weight('desperate', 2*w)
                if self.personality.A:
                    self.change_emotion_weight('relaxed', w)
        else:
            w = abs(self.event.importance * 10)
            if self.personality.C:
                    self.change_emotion_weight('annoyed', 2*w)
            if self.personality.N:
                self.change_emotion_weight('angry', 2*w)
            if self.personality.A:
                self.change_emotion_weight('relaxed', w)
                
        if context == 'individual':
            if self.personality.E:
                self.change_emotion_weight('sad', 10)
            else:
                self.change_emotion_weight('happy', 10)

        if context == 'social':
            if self.personality.E:
                self.change_emotion_weight('happy', 10)
            else:
                self.change_emotion_weight('sad', 10)
                self.change_emotion_weight('annoyed', 10)
            
            if self.event.contribution == 0:
                if self.personality.N:
                    self.change_emotion_weight('angry', 20)
                    self.change_emotion_weight('fear', 20)
                if self.personality.A:
                    self.change_emotion_weight('relaxed', 10)
                    self.change_emotion_weight('peaceful', 10)
            else:
                if self.personality.N:
                    self.change_emotion_weight('excited', 20)
                    self.change_emotion_weight('pleasant', 20)
        
    def regulate(self):
        if self.event.total_progress:
            w = self.event.total_progress * 10
            self.change_emotion_weight('happy', w) 
            
        if self.event.total_progress == 1:
            self.change_emotion_weight('excited', 100)
            self.change_emotion_weight('pleasant', 100)
    
    def normalize_weights(self):
        # normalize weights
        tmp_sum = sum(self.emotions_weight.values())
        self.emotions_weight = {emo: self.emotions_weight[emo]/tmp_sum for emo in self.emotions_weight}
                
    def calculate_emotion(self):
        # calculate the valence, arousal values of the final dominant emotion
        self.normalize_weights()
        x, y = 0, 0
        for e in EmotionSpace.emotions:
            x += self.emotions_weight[e]*self.default_emotions[e]["x"]
            y += self.emotions_weight[e]*self.default_emotions[e]["y"]
        self.emotion = Emotion(**{"x": x, "y": y})
        
    # def mood_regulation(self):
    #     x, y = self.emotion.x, self.emotion.y
    #     x = 0.8*x + 0.2*self.mood[0]
    #     y = 0.8*y + 0.2*self.mood[1]
    #     self.emotion = Emotion(**{"x": x, "y": y})
    #     self.current_emotion = Emotion(**{"x": x, "y": y})
        
    def get_emotion(self):
        return self.emotion