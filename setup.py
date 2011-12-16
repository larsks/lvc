import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name='lvc',
        version='7',
#        install_requires=[
#            'libvirt',
#            ],
        description='Commands for managing a cluster of libvirt hosts.',
        long_description=read('README.rst'),
        author='Lars Kellogg-Stedman',
        author_email='lars@seas.harvard.edu',
        packages=['lvc'],
        entry_points={
            'console_scripts': [
                'lvc = lvc:main',
            ]
            }
        )

