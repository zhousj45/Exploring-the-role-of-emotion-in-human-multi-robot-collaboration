import cozmo
import asyncio
import sys
import random
from cozmo.util import distance_mm, degrees
import time

def ready(robot):
	# set robot to ready position
    robot.set_lift_height(0, in_parallel=True)
    robot.set_head_angle(degrees(0), in_parallel=True)
    robot.wait_for_all_actions_completed()

def cozmo_program(robot: cozmo.robot.Robot):
 	# display expressions one by one
    anim_dict = {"happy": cozmo.anim.Triggers.ComeHere_AlreadyHere, 
    "annoyed_s": cozmo.anim.Triggers.CodeLabUnhappy,
    "annoyed_h": cozmo.anim.Triggers.CodeLabFrustrated,
    "excited": cozmo.anim.Triggers.CubePounceWinSession,
    "suprised": cozmo.anim.Triggers.CodeLabHiccup,
    "desperate": cozmo.anim.Triggers.CodeLabDejected,
    "fear": cozmo.anim.Triggers.CodeLabScaredCozmo,
    "angry": cozmo.anim.Triggers.MajorFail,
    "tired": cozmo.anim.Triggers.ConnectWakeUp_SevereEnergy,
    "bored": cozmo.anim.Triggers.CodeLabBored,
    "sad": cozmo.anim.Triggers.VC_Refuse_energy,
    "relaxed": cozmo.anim.Triggers.CodeLabWin,
    "pleasant": cozmo.anim.Triggers.BuildPyramidThirdBlockUpright}

    # randomly shuffled list is kept
    anim_list = ['sad', 'tired', 'relaxed', 'bored', 'suprised', 'fear', 'pleasant', 'annoyed_s', 'angry', 'desperate', 'happy', 'annoyed_h', 'excited']
    

    i = 0
    while True:
        start = input("Please press enter to perform next expression: ")
        if start == "q":
            break
        ready(robot)
        if start == "r":
            i -= 1
            print(str(anim_list[i]))
            robot.play_anim_trigger(anim_dict[anim_list[i]], ignore_lift_track=True).wait_for_completed()
        else:
            print(str(anim_list[i]))
            robot.play_anim_trigger(anim_dict[anim_list[i]], ignore_lift_track=True).wait_for_completed()
        i += 1


cozmo.run_program(cozmo_program)