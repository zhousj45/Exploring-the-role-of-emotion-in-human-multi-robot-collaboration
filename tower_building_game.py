import cozmo
import asyncio
import sys
import random
from cozmo.util import distance_mm, speed_mmps, degrees, Pose
from random import randint


class Agent:

    def __init__(self, robot, type):
        self.robot = robot
        self.world = robot.world
        self.behavior = None
        self.action = None
        self.cubes = None
        self.cubes_dist = None
        self.min_dist_cube_id = None
        self.flag = False
        self.animation = None
        self.type = type

    def calculate_dist(self, cube):
        # calculate the distance between the robot and the cube
        translation = self.robot.pose - cube.pose
        return ((translation.position.x / 100) ** 2) + ((translation.position.y / 100) ** 2)

    def get_cubes_dists(self, cubes):
        # get distances between the robot and three cubes
        self.cubes_dist = {cube.cube_id: self.calculate_dist(cube) for cube in cubes}

    def get_n_min_dist_cube_id(self, n=1):
        # find the closest cube out of 3
        if not self.cubes_dist:
            raise Exception("no cubes recognized now")
        self.min_dist_cube_id = list(filter(
            lambda cube_id: self.cubes_dist[cube_id] == sorted(self.cubes_dist.values())[n-1], self.cubes_dist))[0]

    def set_behavior(self, behavior):
        if self.behavior is not None:
            raise Exception("already assigned behaviors, stop first")
        self.behavior = self.robot.start_behavior(behavior)

    def stop_behavior(self):
        if not self.behavior:
            raise Exception("No behavior assigned")
        self.behavior.stop()
        self.behavior = None

    def celebrity(self):
        self.animation = self.robot.play_anim_trigger(cozmo.anim.Triggers.OnSpeedtapGameCozmoWinHighIntensity)

    async def recognize_cubes(self):
        # the robot look around to find 3 cubes. For conveniences, cubes are placed in front of robots. Once the robots
        # turn to an angle that cannot find cube, the robots is forced to turn to original angle and drive back for a
        # short distance, then start looking again.
        flag = True
        while flag:

            look_around = self.robot.start_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)
            try:
                self.cubes = await self.world.wait_until_observe_num_objects(num=3,
                                                                             object_type=cozmo.objects.LightCube,
                                                                             timeout=5)
            except asyncio.TimeoutError:
                print("don't find cube")
            else:
                look_around.stop()
                if len(self.cubes) == 3:
                    # after cubes are found, robots show behaviors according to personality group
                    if self.type == "rational":
                        pass
                    else:
                        await self.robot.play_anim_trigger(cozmo.anim.Triggers.ComeHere_AlreadyHere).wait_for_completed()
                    flag = False

            await self.robot.turn_in_place(degrees(0), is_absolute=True).wait_for_completed()
            await self.robot.drive_straight(distance_mm(-20), speed_mmps(50)).wait_for_completed()


class MultiAgents:

    def __init__(self, *args):
        self.type = args[2]
        self.agent_x, self.agent_y = Agent(args[0], self.type), Agent(args[1], self.type)
        self.agents_id = {1: self.agent_x, 2: self.agent_y}
        self.targs = {1: {"pick_targ": None, "place_targ": None}, 2: {"pick_targ": None, "place_targ": None}}
        self.flag = True # True means the robot is going to stack the second-layer
        self.mid_cube = None

    def who_last(self):
        # randomly choose one robot
        return random.choice(list(self.agents_id))

    def calculate_cubes_params(self):
        # calculate cube-robot distance for two robots and get the cube with shortest distance. if the closest cubes are
        # same, randomly choose one robot to find the second close cube.
        self.agent_x.get_cubes_dists(self.agent_x.cubes)
        self.agent_y.get_cubes_dists(self.agent_y.cubes)

        self.agent_x.get_n_min_dist_cube_id()
        self.agent_y.get_n_min_dist_cube_id()

        if self.agent_x.min_dist_cube_id == self.agent_y.min_dist_cube_id:
            self.agents_id[self.who_last()].get_n_min_dist_cube_id(n=2)

    def cooperate_assign_cubes(self):
        # assign the closest cube to robots as their "pick up" object, the rest one is assigned as target cube
        place_targ_exclu_ids = [self.agent_x.min_dist_cube_id, self.agent_y.min_dist_cube_id]

        for cube_x in self.agent_x.cubes:

            if cube_x.cube_id == self.agent_x.min_dist_cube_id:
                self.targs[1]["pick_targ"] = cube_x
            if cube_x.cube_id not in place_targ_exclu_ids:
                self.targs[1]["place_targ"] = cube_x

        for cube_y in self.agent_y.cubes:

            if cube_y.cube_id == self.agent_y.min_dist_cube_id:
                self.targs[2]["pick_targ"] = cube_y
            if cube_y.cube_id not in place_targ_exclu_ids:
                self.targs[2]["place_targ"] = cube_y

    async def agent_plays_cube(self, aid):
        # one robot stack its "pick up" cube on target cube, the other one place its "pick up" cube to a predefined
        # position where both robots can observe the cube.
        agent = self.agents_id[aid]

        while True:
            action = agent.robot.pickup_object(self.targs[aid]["pick_targ"], num_retries=1)
            await action.wait_for_completed()
            if action.has_succeeded:
                break
        x = self.targs[aid]["place_targ"].pose.position.x
        y = self.targs[aid]["place_targ"].pose.position.y
        z = self.targs[aid]["place_targ"].pose.position.z
        if self.flag:
            self_y = agent.robot.pose.position.y
            self.flag = False

            await agent.robot.place_on_object(self.targs[aid]["place_targ"], num_retries=3).wait_for_completed()
            if self.type == "positive":
                await agent.robot.play_anim_trigger(cozmo.anim.Triggers.CodeLabWin, ignore_body_track=False).wait_for_completed()
            elif self.type == "negative":
                await agent.robot.play_anim_trigger(cozmo.anim.Triggers.CodeLabWin, ignore_body_track=False).wait_for_completed()

            # after stacking the second-layer cube, go to the robot and its cube
            await agent.robot.drive_straight(distance_mm(-60), speed_mmps(100)).wait_for_completed()
            if self_y < y:
                await agent.robot.go_to_pose(Pose(x-100, self_y, z, angle_z=degrees(135))).wait_for_completed()
            else:
                await agent.robot.go_to_pose(Pose(x - 150, self_y, z, angle_z=degrees(-135))).wait_for_completed()
            agent.flag = True
            self.mid_cube = self.targs[aid]["pick_targ"]

        else:
            await agent.robot.go_to_pose(Pose(x-200, y, z, angle_z=degrees(0))).wait_for_completed()
            await agent.robot.place_object_on_ground_here(self.targs[aid]["pick_targ"]).wait_for_completed()
            await agent.robot.drive_straight(distance_mm(-30), speed_mmps(30)).wait_for_completed()
            if self.type == "positive":
                await agent.robot.play_anim_trigger(cozmo.anim.Triggers.CodeLabSquint1,
                                                ignore_body_track=False).wait_for_completed()
            elif self.type == "negative":
                await agent.robot.play_anim_trigger(cozmo.anim.Triggers.CodeLabNo,
                                                    ignore_body_track=False).wait_for_completed()

    async def talk(self):
        # robots communicate with expressions corresponding to their personality
        choices_bad = [cozmo.anim.Triggers.FrustratedByFailure, cozmo.anim.Triggers.CodeLabNo,
                       cozmo.anim.Triggers.BuildPyramidFirstBlockOnSide, cozmo.anim.Triggers.CodeLabFrustrated,
                       cozmo.anim.Triggers.AskToBeRightedRight, cozmo.anim.Triggers.AskToBeRightedLeft,
                       cozmo.anim.Triggers.CozmoSaysBadWord]
        choices_good = [cozmo.anim.Triggers.CodeLabChatty, cozmo.anim.Triggers.CodeLabReactHappy,
                        cozmo.anim.Triggers.CodeLabTakaTaka, cozmo.anim.Triggers.CodeLabThinking,
                        cozmo.anim.Triggers.CodeLabWondering, cozmo.anim.Triggers.CozmoSaysSpeakGetInLong,
                        cozmo.anim.Triggers.BuildPyramidFirstBlockUpright, cozmo.anim.Triggers.PutDownBlockPutDown]

        if self.type == "positive":
            choices = choices_good
        elif self.type == "negative":
            choices = choices_bad
        await self.agent_x.robot.play_anim_trigger(random.choice(choices), ignore_body_track=True).wait_for_completed()
        await self.agent_y.robot.play_anim_trigger(random.choice(choices), ignore_body_track=True).wait_for_completed()
        await self.agent_x.robot.play_anim_trigger(random.choice(choices), ignore_body_track=True).wait_for_completed()
        await self.agent_y.robot.play_anim_trigger(random.choice(choices), ignore_body_track=True).wait_for_completed()

    async def try_hard(self, aid):
        # working hard expression
        agent = self.agents_id[aid]
        await agent.robot.set_lift_height(0.7, accel=10.0, max_speed=1.0, duration=0.0, in_parallel=False,
                              num_retries=0).wait_for_completed()
        await agent.robot.set_lift_height(1, accel=0.1, max_speed=0.1, duration=2.0, in_parallel=False,
                              num_retries=0).wait_for_completed()
        if self.type == "positive" or self.type == "negative":
            await agent.robot.play_anim_trigger(cozmo.anim.Triggers.WorkoutStrongLift_lowEnergy,
                                ignore_lift_track=True).wait_for_completed()

    async def try_three_layer(self, aid):
        # try to stack the top-layer cube
        agent = self.agents_id[aid]
        y = self.targs[aid]["place_targ"].pose.position.y
        if agent.flag:
            self_y = agent.robot.pose.position.y
            if self.type == "positive" or self.type == "negative":
                await agent.robot.play_anim_trigger(cozmo.anim.Triggers.CodeLabConducting).wait_for_completed()
            if self_y < y:
                await agent.robot.turn_in_place(degrees(45), is_absolute=True).wait_for_completed()
            else:
                await agent.robot.turn_in_place(degrees(-45), is_absolute=True).wait_for_completed()

        else:
            await agent.robot.pickup_object(self.targs[aid]["pick_targ"], num_retries=1).wait_for_completed()
            await agent.robot.go_to_object(self.targs[aid]["place_targ"], distance_from_object=distance_mm(100)).wait_for_completed()
            if self.type == "positive":
                num_of_tries = 3
            elif self.type == "negative":
                num_of_tries = 1
            else:
                num_of_tries = 2
            for i in range(num_of_tries):
                await self.try_hard(aid)

            if self.type == 'positive':
                await agent.robot.drive_straight(distance_mm(-30), speed_mmps(100)).wait_for_completed()
                await agent.robot.place_object_on_ground_here(self.targs[aid]["pick_targ"]).wait_for_completed()
                await agent.robot.play_anim_trigger(cozmo.anim.Triggers.CodeLabDejected).wait_for_completed()
            elif self.type == 'negative':
                await agent.robot.drive_straight(distance_mm(-30), speed_mmps(100)).wait_for_completed()
                await agent.robot.play_anim_trigger(cozmo.anim.Triggers.MajorFail).wait_for_completed()
            else:
                await agent.robot.place_object_on_ground_here(self.targs[aid]["pick_targ"]).wait_for_completed()

    async def search_face(self, aid, round):
        # looking for human face
        agent = self.agents_id[aid]
        face = None
        await agent.robot.turn_in_place(degrees(0), is_absolute=True).wait_for_completed()
        for i in range(round):
            await agent.robot.set_head_angle(degrees(20 + i * 20)).wait_for_completed()
            degree = agent.robot.head_angle
            if face:
                agent.robot.set_all_backpack_lights(cozmo.lights.blue_light)
                await agent.robot.play_anim_trigger(cozmo.anim.Triggers.ComeHere_SearchForFace_FoundFace).wait_for_completed()
                await agent.robot.set_head_angle(degree).wait_for_completed()
                asyncio.sleep(2)
                agent.robot.set_all_backpack_lights(cozmo.lights.off_light)
                break
            degree1 = randint(30, 50)

            await agent.robot.turn_in_place(degrees(degree1)).wait_for_completed()
            try:
                face = await agent.robot.world.wait_for_observed_face(timeout=2)
            except asyncio.TimeoutError:
                print("Didn't find a face.")

            degree2 = -randint(30, 50)
            await agent.robot.turn_in_place(degrees(degree2)).wait_for_completed()
            try:
                face = agent.robot.world.wait_for_observed_face(timeout=2)
            except asyncio.TimeoutError:
                print("Didn't find a face.")

    async def seek_for_help(self, aid):
        # expressions during seeking help stage
        agent = self.agents_id[aid]
        if agent.flag:
            await agent.robot.play_anim_trigger(cozmo.anim.Triggers.CodeLabHeadsUp).wait_for_completed()
            await self.search_face(aid, 5)
            await agent.robot.play_anim_trigger(cozmo.anim.Triggers.CodeLabConducting, ignore_body_track=True).wait_for_completed()
        else:
            if self.type == "positive":
                await agent.robot.play_anim_trigger(cozmo.anim.Triggers.CodeLabDejected).wait_for_completed()
            elif self.type == "negative":
                await agent.robot.play_anim_trigger(cozmo.anim.Triggers.CodeLabUnhappy).wait_for_completed()

    async def finished(self, aid1):
        # robots show corresponding expressions based on whether the top-layer cube is stacked with the specified time
        # NOTE: one of the robot must connect to all three cubes, otherwise this method won't work
        cube = self.targs[aid1]["place_targ"]

        print(cube.is_connected)

        try:
            print("Waiting for cube to be tapped")

            await cube.wait_for_tap(timeout=10)
            print("Cube tapped")
        except asyncio.TimeoutError:
            print("No-one tapped our cube :-(")
            anim_x = self.agent_x.robot.play_anim_trigger(cozmo.anim.Triggers.VC_Refuse_energy, ignore_body_track=True,
                                                          ignore_lift_track=True)
            anim_y = self.agent_y.robot.play_anim_trigger(cozmo.anim.Triggers.VC_Refuse_energy, ignore_body_track=True,
                                                          ignore_lift_track=True)
            await anim_x.wait_for_completed()
            await anim_y.wait_for_completed()
        else:
            anim_x = self.agent_x.robot.play_anim_trigger(cozmo.anim.Triggers.CodeLabWin, ignore_body_track=True,
                                                       ignore_lift_track=True)
            anim_y = self.agent_y.robot.play_anim_trigger(cozmo.anim.Triggers.CodeLabWin, ignore_body_track=True,
                                                   ignore_lift_track=True)
            await anim_x.wait_for_completed()
            await anim_y.wait_for_completed()


def main(sdk_1, sdk_2, loop):
    # the whole procedure of tower building game
    async def init(sdk1, sdk2):
        # initialize two robots and their connections
        robot_x = await sdk1.wait_for_robot()
        robot_y = await sdk2.wait_for_robot()

        multi_agents = MultiAgents(robot_x, robot_y, "negative")
        return multi_agents
    # initialize connections to two robots
    agents = loop.run_until_complete(init(sdk_1, sdk_2))
    # robots finding cubes
    loop.run_until_complete(asyncio.gather(agents.agents_id[1].recognize_cubes(), agents.agents_id[2].recognize_cubes()))
    # calculate robot-cube distances
    agents.calculate_cubes_params()
    # assign cubes based on distances
    agents.cooperate_assign_cubes()
    # one robot stack second-layer cube, the other one place the cube to predefined position
    loop.run_until_complete(asyncio.gather(agents.agent_plays_cube(1), agents.agent_plays_cube(2)))
    # robots in emotional groups have explicit communication
    if agents.type != "rational":
        loop.run_until_complete(agents.talk())
    # robots try to stack top-layer cube
    loop.run_until_complete(asyncio.gather(agents.try_three_layer(1), agents.try_three_layer(2)))
    # robots expressions during seeking help stage
    loop.run_until_complete(asyncio.gather(agents.seek_for_help(1), agents.seek_for_help(2)))
    # robots reaction to the game result
    loop.run_until_complete(agents.finished(1))


if __name__ == '__main__':

    cozmo.setup_basic_logging()
    al_loop = asyncio.get_event_loop()
    cozmo.robot.Robot.drive_off_charger_on_connect = False
    # Connect to both robots

    try:
        conn1 = cozmo.connect_on_loop(al_loop)
        conn2 = cozmo.connect_on_loop(al_loop)
    except cozmo.ConnectionError as e:
        sys.exit("A connection error occurred: %s" % e)

    main(conn1, conn2, al_loop)

