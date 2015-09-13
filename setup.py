# Copyright 2015 Artur Chakhvadze. All Rights Reserved.

"""Community class."""

__author__ = 'Artur Chakhvadze (norpadon@yandex.ru)'

from setuptools import setup, find_packages

setup(
    name='vk_miner',
    version='0.1',

    author='Artur Chakhvadze',
    author_email='norpadon@yandex.com',

    url='https://github.com/norpadon/vk_miner',
    description='Tool for loading data from vk.com',

    packages=find_packages(),
    install_requires=[
        'requests',
        'pandas',
        'geopy',
        'coverage',
        'tables',
        'networkx',
        'scipy',
        'numpy',
        'pandas',
        'scikit-learn',
        'matplotlib',
        'geopy',
        'mplleaflet'
    ],

    license='MIT License',
    classifiers=[],
    keywords='vk.com',
)
