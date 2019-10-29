import math
import numpy as np


class EmotionVector:

    def __init__(self, **kwargs):
        if "strength" in kwargs and "angle" in kwargs:
            # strength -> [0, 1]
            self.strength = None
            # angle -> [0, 360]
            self.angle = None
            self.set_strength_angle(kwargs["strength"], kwargs["angle"])
        elif "x" in kwargs and "y" in kwargs:
            self.x = None
            self.y = None
            self.set_xy(kwargs["x"], kwargs["y"])

    def set_strength_angle(self, strength, angle):
        self.strength = strength
        self.angle = angle
        self.x = strength * math.cos(math.radians(angle))
        self.y = strength * math.sin(math.radians(angle))

    def set_xy(self, x, y):
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mapper = EmotionSpace.mapper
        self.area = None

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

    def __repr__(self):
        return "emotion: {}, ({:.2f}, {:.2f}), \n angle: {:.2f}, strength: {:.2f}".format(
            self.get_emotion(), self.x, self.y, self.angle, self.strength)


coordinates =[{"x": math.sqrt(2)/4, "y": math.sqrt(2)/4},
{"x": math.sqrt(2)/4, "y": -math.sqrt(2)/4},
{"x": -math.sqrt(2)/4, "y": math.sqrt(2)/4},
{"x": -math.sqrt(2)/4, "y": -math.sqrt(2)/4},
{"x": math.sqrt(2)/4, "y": (0.9+math.sqrt(2))/2},
{"x": math.sqrt(2)/4, "y": -(0.9+math.sqrt(2))/2},
{"x": -math.sqrt(2)/4, "y": (0.9+math.sqrt(2))/2},
{"x": -math.sqrt(2)/4, "y": -(0.9+math.sqrt(2))/2},
{"x": (0.9+math.sqrt(2))/2, "y": math.sqrt(2)/4},
{"x": (0.9+math.sqrt(2))/2, "y": -math.sqrt(2)/4},
{"x": -(0.9+math.sqrt(2))/2, "y": math.sqrt(2)/4},
{"x": -(0.9+math.sqrt(2))/2, "y": -math.sqrt(2)/4},
{"x": 0, "y": 0.95},
{"x": 0, "y": -0.95}
]


v = []
for each in coordinates:
    ev = Emotion(**each)
    v.append(ev)
