#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import numpy as np

try:
    from pylibfreenect2 import Freenect2, SyncMultiFrameListener
    from pylibfreenect2 import FrameType, Registration, Frame
    FREENECT2_AVAILABLE = True
except ImportError:
    FREENECT2_AVAILABLE = False

class KinectNode(Node):
    def __init__(self):
        super().__init__('kinect_node')
        
        if not FREENECT2_AVAILABLE:
            self.get_logger().error('pylibfreenect2 no está instalado')
            return
            
        self.bridge = CvBridge()
        
        # Publishers
        self.rgb_pub = self.create_publisher(Image, '/camera/rgb/image_raw', 10)
        self.depth_pub = self.create_publisher(Image, '/camera/depth/image_raw', 10)
        
        # Inicializar Kinect
        self.fn = Freenect2()
        num_devices = self.fn.enumerateDevices()
        
        if num_devices == 0:
            self.get_logger().error('No se encontró Kinect')
            return
            
        serial = self.fn.getDeviceSerialNumber(0)
        self.device = self.fn.openDevice(serial)
        
        self.listener = SyncMultiFrameListener(FrameType.Color | FrameType.Depth)
        self.device.setColorFrameListener(self.listener)
        self.device.setIrAndDepthFrameListener(self.listener)
        
        self.device.start()
        
        # Timer para publicar
        self.timer = self.create_timer(0.033, self.publish_frames)  # ~30 FPS
        
        self.get_logger().info('Kinect Node iniciado')
    
    def publish_frames(self):
        frames = self.listener.waitForNewFrame()
        
        color = frames['color']
        depth = frames['depth']
        
        # Publicar RGB
        rgb_msg = self.bridge.cv2_to_imgmsg(color.asarray(), encoding='bgr8')
        self.rgb_pub.publish(rgb_msg)
        
        # Publicar Depth
        depth_msg = self.bridge.cv2_to_imgmsg(depth.asarray(), encoding='32FC1')
        self.depth_pub.publish(depth_msg)
        
        self.listener.release(frames)

def main(args=None):
    rclpy.init(args=args)
    node = KinectNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
