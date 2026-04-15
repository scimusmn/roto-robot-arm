from setuptools import find_packages, setup

package_name = 'js_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='exhibits',
    maintainer_email='exhibits@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
        	'publisher = js_control.publisher:main',
        	'subscriber = js_control.subscriber:main',
        	'axis = js_control.axis:main',
        	'polar = js_control.polar:main',
        ],
    },
)
