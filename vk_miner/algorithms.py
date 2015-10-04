# Copyright 2015 Artur Chakhvadze. All Rights Reserved.

"""Algorithms for vk graph mining."""

__author__ = 'Artur Chakhvadze (norpadon@yandex.ru)'

from itertools import *
from functools import *

import pandas as pd
from tornado import gen

from vk_async.exceptions import VkAPIMethodError
from vk_miner.community import Community
from vk_miner.utils import *


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

    cities, universities, groups, users = preloaded or [{} for _ in range(4)]
    friends, members = [[], []]

    def load_users(user_ids):
        """Load users with given ids."""

        def mapper(uid_pack):
            return api.users.get(user_ids=uid_pack, fields=user_fields)

        result = map_async(mapper, grouper(user_ids, max_users_per_query))

        return [
            parse_user(item, users, cities, universities)
            for item in chain(*result)
        ]

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

        def parse_item(item):
            if 'groups' in item and item['groups']:
                subscriptions = [
                    parse_group(it, groups)
                    for it in item['groups']
                ]
            else:
                subscriptions = []

            if 'friends' in item and item['friends']:
                friendlist = [
                    parse_user(entry, users, cities, universities)
                    for entry in item['friends']
                    if 'deactivated' not in entry
                ]
            else:
                friendlist = []

            return friendlist, subscriptions

        @gen.coroutine
        def mapper(uid):
            try:
                result = yield api.execute.getUserData(user_id=uid)
                log_user_loaded()
                return parse_item(result)
            except VkAPIMethodError as e:
                print(e)
                return {}

        return map_async(mapper, user_ids)

    print('Loading roots...', flush=True)
    visited = set()
    not_visited = set(load_users(roots))
    layers = {u: 0 for u in not_visited}

    for i in range(1, depth + 1):
        print(
            'Loading users from layer {0} of {1}:'.format(i, depth),
            flush=True
        )

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


def load_group_members(api, group_id):
    """Load graph of group members.

    Args:
        api: instance of vk_async api to make queries from.
        group_id: id of group.

    Returns:
        Community object with loaded data.
    """
    cities, universities, groups, users = [{} for _ in range(4)]

    def mapper(group_id):
        return api.execute.getCommunityMembers(group_id=group_id)

    print("Loading list of group members...")
    raw_members = map_async(mapper, [group_id])[0]
    members = [
        parse_user(entry, users, cities, universities)
        for entry in raw_members
    ]

    preloaded = cities, universities, groups, users
    return load_friends_bfs(api, members, 1, preloaded).filter_users(
        lambda u: u.layer < 1
    )


