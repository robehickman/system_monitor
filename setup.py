from setuptools import setup

setup(
    name='system monitor',
    version='0.1',
    description='Network enabled system monitor',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='Network system monitor',
    author='Robert Hickman',
    author_email='robehickman@gmail.com',
    license='MIT',
    packages=['system_monitor'],
    install_requires=[
        'pysdl2',
        'pysdl2-dll',
        'psutil',
    ],
    scripts=['monitor_server.py'],
    zip_safe=False)

