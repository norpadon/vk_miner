# Copyright 2015 Artur Chakhvadze. All Rights Reserved.

"""Auxiliaty functions."""

__author__ = 'Artur Chakhvadze (norpadon@yandex.ru)'

from collections import namedtuple
from itertools import *
from datetime import datetime

import geopy
from tornado.ioloop import IOLoop
from tornado import gen

city_cache = {}


def get_coordinates(city):
    """Load latitude and longitude of city with given name.

    Args:
        city: name of the city.

    Returns:
        (latitude, longitude) of city or (None, None) if city is unknown.
    """
    if city not in city_cache:
        geocoder = geopy.geocoders.Yandex()

        try:
            location = geocoder.geocode(city)
        except:
            location = None

        if location:
            city_cache[city] = (location.latitude, location.longitude)
        else:
            city_cache[city] = (None, None)

    return city_cache[city]


def map_async(mapper, data):
    """Map asynchronous computation over data and collect result.

    Args:
        mapper: function of kind a -> Future b.
        data: list of a.

    Returns:
        List of b.
    """
    result = None

    @gen.coroutine
    def compute():
        nonlocal result
        result = yield [mapper(elem) for elem in data]

    loop = IOLoop.current()
    loop.run_sync(compute)

    return result


User = namedtuple(
    'User',
    ['name', 'age', 'city_id', 'university_id', 'last_seen']
)


def parse_user(entry, users, cities, universities):
    """Load user's data from it's dict'ed JSON representation
    and store it in the given tables.

    Args:
        entry: dict containing user's data.
        users: mapping from user ids to users.
        cities: mapping from city ids to city names.
        universities: mapping from university ids to university names.

    Returns:
        Id of parsed user.
    """
    uid = int(entry['id'])
    name = entry['first_name'] + ' ' + entry['last_name']

    university_name, university_id = None, None
    if 'universities' in entry and entry['universities']:
        university_name = entry['universities'][0]['name'].strip()
        university_id = int(entry['universities'][0]['id'])
        universities[university_id] = university_name

    city_name, city_id = None, None
    if 'city' in entry and entry['city']:
        city_name = entry['city']['title'].strip()
        city_id = int(entry['city']['id'])
        cities[city_id] = city_name

    age = None
    if 'bdate' in entry and entry['bdate']:
        dmy = entry['bdate'].split('.')
        if len(dmy) == 3:
            age = 2015 - int(dmy[2])

    last_seen = datetime.min
    if 'last_seen' in entry and entry['last_seen']:
        last_seen = int(entry['last_seen']['time'])
        last_seen = str(datetime.fromtimestamp(last_seen))

    users[uid] = User(name, age, city_id, university_id, last_seen)
    return uid


def parse_group(entry, groups):
    """Load group data from it's dict'ed JSON representation
    and store it in table.

    Args:
        groups: mapping from group ids to group names.

    Returns:
        Id of parsed group.
    """
    group_name = entry['name'].strip()
    group_id = int(entry['id'])
    groups[group_id] = group_name
    return group_id


def load_city(name):
    """Load city data from it's name."""
    latitude, longitude = get_coordinates(name)
    return [name, latitude, longitude]


def grouper(iterable, n):
    """Collect data into fixed-length chunks or blocks."""
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF G
    args = [iter(iterable)] * n
    return [
        filter(None.__ne__, pack)
        for pack in zip_longest(fillvalue=None, *args)
    ]
