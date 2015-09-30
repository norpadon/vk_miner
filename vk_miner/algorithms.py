# Copyright 2015 Artur Chakhvadze. All Rights Reserved.

"""Algorithms for vk graph mining."""

__author__ = 'Artur Chakhvadze (norpadon@yandex.ru)'

import geopy
import logging
import pandas as pd

from tornado.ioloop import IOLoop
from tornado import gen

from vk_miner.community import Community
from itertools import *
from collections import deque, namedtuple
from datetime import datetime, timedelta

logger = logging.getLogger('vk_miner')

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
        except Exception as e:
            logger.warning(e)
            location = None

        if location:
            city_cache[city] = (location.latitude, location.longitude)
        else:
            city_cache[city] = (None, None)

    return city_cache[city]


def load_friends_bfs(api, roots, depth, preloaded=None):
    """Load graph of friends via breadth-first-search.

    Args:
        api: instance of vk_async api to make queries from.
        roots: list of users, whose friends we need to load.
        depth: maximal distance between root and loaded user.
        preloaded: preloaded data that should be appended to result.

    Returns:
        Community object with loaded data.
        Subscriptions of users from last layer are not collected.
    """

    max_users_per_query = 1000
    user_fields = 'universities, schools, city, bdate, last_seen'

    cities, universities, groups, users = preloaded or [{} for i in range(4)]
    friends, members = [[], []]

    User = namedtuple(
        'User',
        ['name', 'age', 'city_id', 'university_id', 'last_seen']
    )

    def parse_user(entry):
        """Load user's data from it's dict'ed JSON representation."""

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
            last_seen = datetime.fromtimestamp(last_seen)

        users[uid] = User(name, age, city_id, university_id, last_seen)
        return uid

    def parse_group(entry):
        """Load group data from it's dict'ed JSON representation."""
        group_name = entry['name'].strip()
        group_id = int(entry['id'])
        groups[group_id] = group_name
        return group_id

    def load_city(name):
        """Load city data from it's name."""
        latitude, longitude = get_coordinates(name)
        return [name, latitude, longitude]

    def grouper(iterable, n):
        """Collect data into fixed-length chunks or blocks"""
        # grouper('ABCDEFG', 3, 'x') --> ABC DEF G
        args = [iter(iterable)] * n
        return [
            filter(None.__ne__, pack)
            for pack in zip_longest(fillvalue=None, *args)
        ]

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

    def load_users(user_ids):
        """Load users with given ids."""

        def mapper(uid_pack):
            return api.users.get(user_ids=uid_pack, fields=user_fields)

        result = map_async(mapper, grouper(user_ids, max_users_per_query))

        return [parse_user(item) for item in chain(*result)]

    def load_friends(user_ids):
        """Load friends of users with given ids."""
        counter = 0

        def log_user_loaded():
            nonlocal counter
            counter += 1
            print(
                '{} of {} users loaded'.format(counter, len(user_ids)),
                end='\r',
                flush=True,
            )

        @gen.coroutine
        def mapper(uid):
            result = yield api.execute.getUserData(user_id=uid)
            log_user_loaded()
            return result

        result = map_async(mapper, user_ids)

        def parse_item(item):
            if 'groups' in item and item['groups']:
                subscriptions = [parse_group(it) for it in item['groups']]
            else:
                subscriptions = []

            if 'friends' in item and item['friends']:
                friendlist = [
                    parse_user(entry)
                    for entry in item['friends']
                    if 'deactivated' not in entry
                ]
            else:
                friendlist = []

            return friendlist, subscriptions

        return [parse_item(item) for item in result]

    print('Loading roots...', flush=True)
    visited = set()
    not_visited = set(load_users(roots))
    layers = {u: 0 for u in roots}
    for i in range(1, depth + 1):
        print('Loading users from layer {0} of {1}:'.format(i, depth), flush=True)

        queue = list(not_visited)
        chunk = load_friends(queue)
        new_layer = set()
        for j, pair in enumerate(chunk):
            friendlist, subscriptions = pair
            uid = queue[j]
            for fid in friendlist:
                friends.extend([(uid, fid), (fid, uid)])
            for gid in subscriptions:
                members.append((gid, uid))

            new_layer.update(friendlist)

        visited.update(not_visited)
        new_layer -= visited
        not_visited = new_layer
        for u in new_layer:
            layers[u] = i

    friend_keys, friend_values = list(zip(*friends))
    member_keys, member_values = list(zip(*members))

    # Load geographical data.
    print('Loading geodata...', flush=True)

    for c in cities:
        cities[c] = load_city(cities[c])

    print('Done!', flush=True)

    return Community(
        users=pd.DataFrame.from_items(
            users.items(),
            orient='index',
            columns=User._fields
        ),
        cities=pd.DataFrame.from_items(
            cities.items(),
            orient='index',
            columns=['city', 'latitude', 'longitude']
        ),
        universities=pd.Series(
            list(universities.values()),
            name='university',
            index=list(universities.keys())
        ),
        groups=pd.Series(
            list(groups.values()),
            name='group',
            index=list(groups.keys())
        ),
        friends=pd.Series(friend_values, index=friend_keys),
        members=pd.Series(member_values, index=member_keys),
        user_attributes=pd.Series(
            list(layers.values()),
            index=[list(layers.keys()), ['layer'] * len(layers)]
        )
    )

