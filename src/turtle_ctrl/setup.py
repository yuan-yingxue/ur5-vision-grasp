from glob import glob

from setuptools import find_packages, setup

package_name = 'turtle_ctrl'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='xuzexin',
    maintainer_email='xuzexin@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'circle = turtle_ctrl.circle:main',
            'pose_listener = turtle_ctrl.pose_listener:main',
            'param_circle = turtle_ctrl.param_circle:main',
            'tf_demo = turtle_ctrl.tf_demo:main',
            'detector = turtle_ctrl.detector:main',
            'grasp_pose = turtle_ctrl.grasp_pose:main',
            'detector_seg = turtle_ctrl.detector_seg:main',
            'grasp_pose_v3 = turtle_ctrl.grasp_pose_v3:main',
            'grasp_executor = turtle_ctrl.grasp_executor:main',
            'image_cycler = turtle_ctrl.image_cycler:main',
            'add_table = turtle_ctrl.add_table:main',
            'det_view = turtle_ctrl.det_view:main',
        ],
    },
)
