import math
import rclpy
from rclpy.node import Node
from flight_control_py.tool.PID import PID
from flight_control_py.flight.base_control import BaseControl as FlightControl
from flight_control_py.flight.flight_controller_info import FlightInfo
from flight_control_py.aruco_visual.aruco import Aruco
from flight_control.srv import GetCloestAruco
from aruco_msgs.msg import Marker


class Mission:
    """
    包含都個任務的class，用於導航，降落等功能
    """

    def __init__(
        self, controller: FlightControl, flight_info: FlightInfo, node: Node
    ) -> None:
        self.controller = controller
        self.flight_info = flight_info
        self.node = node
        self.cloest_aruco = None
        # self.getCloestArucoClient = self.node.create_client(GetCloestAruco, 'get_cloest_aruco')
        self.sub = self.node.create_subscription(
            Marker, "cloest_aruco", self.cloest_aruco_callback, 10
        )

    def cloest_aruco_callback(self, msg):
        self.cloest_aruco = Aruco(msg.id).fromMsgMarker2Aruco(msg)

    def landedOnPlatform(self):
        """
        Function to control the drone to land on a platform using Aruco markers.

        This function continuously checks the closest Aruco marker detected by the ArucoDetector.
        It calculates the distance and orientation between the drone and the marker.
        The drone moves towards the marker until the distance is less than 0.1 meters.
        If the drone's altitude is lower than the specified lowest_high value, it moves down towards the platform.
        Once the drone has landed on the platform, it stops moving and lands completely.

        Returns:
            None
        """
        # --------------------------------- variable --------------------------------- #
        lowest_high = 0.7  # 最低可看到aruco的高度 單位:公尺
        max_speed = 0.3  # 速度 單位:公尺/秒
        max_yaw = 15 * 3.14 / 180  # 15度
        downward_speed = -0.2  # the distance to move down
        # todo 刪除pid控制程式
        pid_x = PID(
            0.2,
            0,
            0,
            0,
            time=self.controller.node.get_clock().now().nanoseconds * 1e-9,
        )
        pid_y = PID(
            0.2,
            0,
            0,
            0,
            time=self.controller.node.get_clock().now().nanoseconds * 1e-9,
        )
        pid_yaw = PID(
            0.1,
            0.05,
            0,
            0,
            time=self.controller.node.get_clock().now().nanoseconds * 1e-9,
        )
        last_moveup_time = rclpy.clock.Clock().now()
        while True:
            # rclpy.spin_once(self.flight_info.node)
            # ----------------------- get downward aruco coordinate ---------------------- #
            closest_aruco = self.cloest_aruco
            if closest_aruco is None:
                if rclpy.clock.Clock().now() - last_moveup_time > rclpy.time.Duration(
                    seconds=0.5
                ):
                    if self.flight_info.rangefinder_alt < 3:
                        # print('move up')
                        self.controller.sendPositionTargetVelocity(0, 0, 0.2, 0)
                        last_moveup_time = rclpy.clock.Clock().now()
                # self.controller.setZeroVelocity()
                continue
            marker_x, marker_y, marker_z, marker_yaw, _, _ = (
                closest_aruco.getCoordinate()
            )
            if (
                marker_x is None
                or marker_y is None
                or marker_z is None
                or marker_yaw is None
            ):
                if rclpy.clock.Clock().now() - last_moveup_time > rclpy.time.Duration(
                    seconds=0.5
                ):
                    if self.flight_info.rangefinder_alt < 3:
                        # print('move up')
                        self.controller.sendPositionTargetVelocity(0, 0, 0.2, 0)
                        last_moveup_time = rclpy.clock.Clock().now()
                # self.controller.setZeroVelocity()
                continue
            last_moveup_time = rclpy.clock.Clock().now()
            # -------------------------------- PID control ------------------------------- #
            # todo 刪除pid控制程式
            move_x = pid_x.PID(
                marker_x, self.controller.node.get_clock().now().nanoseconds * 1e-9
            )
            move_y = pid_y.PID(
                marker_y, self.controller.node.get_clock().now().nanoseconds * 1e-9
            )
            move_yaw = pid_yaw.PID(
                marker_yaw, self.controller.node.get_clock().now().nanoseconds * 1e-9
            )  # convert to radians
            # print(f"x:{move_x}, y:{move_y}, yaw:{move_yaw}, high:{self.flight_info.rangefinder_alt}")
            diffrent_distance = math.sqrt(marker_x**2 + marker_y**2)
            # -------------------------- limit move_x and move_y and move_yaw------------------------- #
            move_x = min(max(-marker_y, -max_speed), max_speed)
            move_y = min(max(-marker_x, -max_speed), max_speed)
            if (360 - marker_yaw) < marker_yaw:
                marker_yaw = -marker_yaw
            move_yaw = min(max(-marker_yaw * 3.14 / 180, -max_yaw), max_yaw)
            # ----------------------------- send velocity command ----------------------------- #
            if (
                diffrent_distance < 0.03
                and self.flight_info.rangefinder_alt <= lowest_high
                and (0 < marker_yaw < 5 or 355 < marker_yaw < 360)
            ):
                self.controller.setZeroVelocity()
                print(f"landing high:{self.flight_info.rangefinder_alt}")
                print(
                    f"x:{marker_x}, y:{marker_y}, z:{marker_z}, yaw:{marker_yaw}, high:{self.flight_info.rangefinder_alt}"
                )
                break
            self.controller.sendPositionTargetPosition(0, 0, 0, yaw=move_yaw)
            if self.flight_info.rangefinder_alt > lowest_high:
                self.controller.sendPositionTargetVelocity(
                    move_x,
                    move_y,
                    downward_speed,
                    0,
                )
            else:
                # when height is lower than lowest_high, stop moving down
                self.controller.sendPositionTargetVelocity(
                    move_x,
                    move_y,
                    0,
                    0,
                )
            print(
                f"move_x:{move_x:.2f}, move_y:{move_y:.2f}, move_yaw:{move_yaw:.2f}, diffrent_distance:{diffrent_distance:.2f}"
            )
        self.controller.setZeroVelocity()
        print("now I want to land=================================")
        while not self.controller.land():
            print("landing")

    def navigateTo(
        self,
        destination_x: float,
        destination_y: float,
        destination_z: float,
        bcn_orient_yaw: float,
    ):
        """
        Function to navigate the drone to a specified location.

        This function uses the PID controller to control the drone's movement.
        The drone moves towards the specified location until it reaches the location.
        The drone stops moving once it reaches the location.

        Args:
            x (float): The x-coordinate of the location.
            y (float): The y-coordinate of the location.
            z (float): The z-coordinate of the location.

        Returns:
            None
        """
        # --------------------------------- variable --------------------------------- #
        max_speed = 0.3
        max_yaw = 15 * 3.14 / 180

        # --------------------------------- function --------------------------------- #
        def around(a, b, threshold=0.5): #如果距離範圍在threshold內就回傳True
            return abs(a - b) < threshold
        last_coordinate_time = self.flight_info.uwb_coordinate.header.stamp #取得最後一次的座標時間
        while (
            # 還沒到指定位置時繼續移動
            not (
                around(self.flight_info.uwb_coordinate.x, destination_x)
                and around(self.flight_info.uwb_coordinate.y, destination_y)
            )
        ):
            if self.flight_info.uwb_coordinate.header.stamp == last_coordinate_time: #如果座標時間沒有更新不要更新移動速度
                continue
            x_diff = destination_x - self.flight_info.uwb_coordinate.x
            y_diff = destination_y - self.flight_info.uwb_coordinate.y
            yaw_diff = math.atan2(y_diff, x_diff) * 180 / math.pi
            compass_heading = self.flight_info.compass_heading
            rotate_deg = 90 - yaw_diff - compass_heading + bcn_orient_yaw
            if 360 - rotate_deg < rotate_deg:
                rotate_deg = -rotate_deg
            move_yaw = min(max(-rotate_deg * 3.14 / 180, -max_yaw), max_yaw)
            move_x = min(max(y_diff, -max_speed), max_speed)
            move_y = min(max(-x_diff, -max_speed), max_speed)
            self.controller.sendPositionTargetPosition(0, 0, 0, yaw=move_yaw)
            self.controller.sendPositionTargetVelocity(move_x, move_y, 0, 0)
        self.controller.setZeroVelocity()

