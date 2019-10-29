import cozmo
import asyncio
import sys
import random
from cozmo.util import distance_mm


class Agent:

    def __init__(self, robot):
        self.robot = robot
        self.world = robot.world
        self.behavior = None
        self.action = None
        self.cubes = None
        self.cubes_dist = None
        self.min_dist_cube_id = None
        self.animation = None

    def calculate_dist(self, cube):
        translation = self.robot.pose - cube.pose
        return ((translation.position.x / 100) ** 2) + ((translation.position.y / 100) ** 2)

    def get_cubes_dists(self, cubes):
        self.cubes_dist = {cube.cube_id: self.calculate_dist(cube) for cube in cubes}

    def get_n_min_dist_cube_id(self, n=1):
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
        self.cubes = await self.world.wait_until_observe_num_objects(num=3, object_type=cozmo.objects.LightCube, timeout=60)


class MultiAgents:

    def __init__(self, *args):
        self.agent_x, self.agent_y = Agent(args[0]), Agent(args[1])
        self.agents_id = {1: self.agent_x, 2: self.agent_y}
        self.targs = {1: {"pick_targ": None, "place_targ": None}, 2: {"pick_targ": None, "place_targ": None}}
        self.flag = True

    def who_last(self):
        return random.choice(list(self.agents_id))

    async def recognize_cubes_together(self):

        self.agent_x.set_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)
        self.agent_y.set_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)

        try:
            await self.agent_x.recognize_cubes()
        except asyncio.TimeoutError:
            print("don't find cube")
        else:
            self.agent_x.stop_behavior()

        try:
            await self.agent_y.recognize_cubes()
        except asyncio.TimeoutError:
            print("don't find cube")
        else:
            self.agent_y.stop_behavior()

        self.agent_x.get_cubes_dists(self.agent_x.cubes)
        self.agent_y.get_cubes_dists(self.agent_y.cubes)

        self.agent_x.get_n_min_dist_cube_id()
        self.agent_y.get_n_min_dist_cube_id()

        if self.agent_x.min_dist_cube_id == self.agent_y.min_dist_cube_id:
            self.agents_id[self.who_last()].get_n_min_dist_cube_id(n=2)

    def cooperate_assign_cubes(self):

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
        agent = self.agents_id[aid]

        while not agent.robot.is_carrying_block:
            await agent.robot.pickup_object(self.targs[aid]["pick_targ"], num_retries=1).wait_for_completed()

        if self.flag:
            await agent.robot.place_on_object(self.targs[aid]["place_targ"], num_retries=3).wait_for_completed()
            self.flag = False
        else:
            await agent.robot.go_to_object(self.targs[aid]["place_targ"],
                                                 distance_from_object=distance_mm(100)).wait_for_completed()
            await agent.robot.place_object_on_ground_here(self.targs[aid]["place_targ"]).wait_for_completed()


def main(sdk_1, sdk_2, loop):

    async def init(sdk1, sdk2):

        robot_x = await sdk1.wait_for_robot()
        robot_y = await sdk2.wait_for_robot()

        multi_agents = MultiAgents(robot_x, robot_y)
        return multi_agents

    agents = loop.run_until_complete(init(sdk_1, sdk_2))
    loop.run_until_complete(agents.recognize_cubes_together())
    agents.cooperate_assign_cubes()

    loop.run_until_complete(asyncio.gather(agents.agent_plays_cube(1), agents.agent_plays_cube(2)))
    # action_1 = asyncio.ensure_future(agents.agent_plays_cube(1), loop=loop)
    # action_2 = asyncio.ensure_future(agents.agent_plays_cube(2), loop=loop)

    # return action_1, action_2


if __name__ == '__main__':

    cozmo.setup_basic_logging()
    # cozmo.setup_basic_logging()
    al_loop = asyncio.get_event_loop()
    cozmo.robot.Robot.drive_off_charger_on_connect = False
    # Connect to both robots
    # NOTE: to connect to a specific device with a specific serial number,
    # create a connector (eg. `cozmo.IOSConnector(serial='abc')) and pass it
    # explicitly to `connect` or `connect_on_loop`
    try:
        conn1 = cozmo.connect_on_loop(al_loop)
        conn2 = cozmo.connect_on_loop(al_loop)
    except cozmo.ConnectionError as e:
        sys.exit("A connection error occurred: %s" % e)

    main(conn1, conn2, al_loop)
    # task = asyncio.ensure_future(main(conn1, conn2), loop=al_loop)
    # Run a coroutine controlling both connections
    # al_loop.run_until_complete(task)

    # print("doing")
    # al_loop.run_until_complete(asyncio.gather(a1, a2))
