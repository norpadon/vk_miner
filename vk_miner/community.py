# Copyright 2015 Artur Chakhvadze. All Rights Reserved.

"""Community class."""

__author__ = 'Artur Chakhvadze (norpadon@yandex.ru)'

import os
from functools import *
from collections import Counter
from json import load, dump

import pandas as pd
import numpy as np
import networkx as nx
import mplleaflet
from matplotlib import pyplot as plt

from vk_miner.utils import User


class Community(object):
    """Community represents set of VK users, groups
    and relations between them.
    """
    class User(object):
        """Wrapper around entry in users table."""
        def __init__(self, owner, uid):
            self.__dict__['owner'], self.__dict__['uid'] = owner, uid
            
        @property
        def friends(self):
            return self.owner._friends[self.uid]
        
        @property
        def groups(self):
            return self.owner._subscriptions[self.uid]

        @property
        def university(self):
            if self.university_id:
                return self.owner._universities[self.university_id]
            else:
                return ''

        @property
        def city(self):
            if self.city_id:
                return self.owner._cities[self.city_id][0]
            else:
                return ''

        def get_neighbourhood_graph(self):
            """Return subgraph induced by users's friends.

            Returns:
                networkx.Graph object.
            """
            neighbours = set(self.friends)
            result = nx.Graph()
            result.add_nodes_from(neighbours)
            for neighbour in neighbours:
                for friend in neighbour.friends:
                    if friend in neighbours:
                        result.add_edge(neighbour, friend)

            return result
        
        def __getattr__(self, name):
            if name in User._fields:
                return getattr(self.owner._users[self.uid], name)
            else:
                return self.owner._user_attributes[self.uid][name]

        def __eq__(self, other):
            return all([
                isinstance(other, self.__class__),
                self.owner is other.owner,
                self.uid == other.uid,
            ])

        def __hash__(self):
            return int(self.uid)

        def __repr__(self):
            return '<Vk User id: {self.uid}, name: {self.name}>'.format(
                self=self
            )

        def __str__(self):
            return str(self.uid) + ' - ' + self.name

        def __copy__(self):
            return self.owner.get_user(self.uid)

        def __deepcopy__(self, memo):
            return self.__copy__()
            
    class Group(object):
        """Wrapper around entry in communities table."""
        def __init__(self, owner, uid):
            self.__dict__['owner'], self.__dict__['uid'] = owner, uid

        @property
        def name(self):
            return self.owner._groups[self.uid]

        @property
        def members(self):
            return self.owner._members[self.uid]

        def __getattr__(self, name):
            return self.owner._group_attributes[self.uid][name]

        def __eq__(self, other):
            return all([
                isinstance(other, self.__class__),
                self.owner is other.owner,
                self.uid == other.uid,
            ])

        def __hash__(self):
            return int(self.uid)

        def __str__(self):
            return str(self.uid) + ' ' + self.name

        def __repr__(self):
            return '<Vk Group id: {self.uid}, name: {self.name}>'.format(
                self=self
            )
        
        def __copy__(self):
            return self.owner.get_group(self.uid)

        def __deepcopy__(self, memo):
            return self.__copy__()
        
    def __init__(self, path=None, **kwargs):
        """Creates new community.

        If file is provided, load community data from it.
        Create empty community otherwise.

        Args:
            path: path to the json file or folder with csv files
                containing community data.
            **kwargs: values of tables.
        """
        self.fields = [
            '_users', '_groups', '_cities', '_universities',
            '_friends', '_members', '_subscriptions',
            '_user_attributes', '_group_attributes',
        ]
        
        if path:
            json = load(open(path))

        for field in self.fields:
            self.__dict__[field] = json[field] if path else {}

        for key, mapping in kwargs.items():
            field = '_' + key
            if field in self.fields:
                self.__dict__[field] = {int(k): v for k, v in mapping.items()}

        for user_id in self._users:
            self._users[user_id] = User(*self._users[user_id])

    def save_json(self, path):
        """Save data to file in JSON format

        Args:
            path: path to file.
        """
        data = {field: self.__dict__[field] for field in self.fields}
        dump(data, open(path, 'w'), indent=2, ensure_ascii=False)

    def filter_users(self, predicate):
        """Get community containing all users that satisfy given predicate.

        Args:
            predicate: function from Community.User to boolean.

        Returns:
            Community object.
        """
        users = {
            user.uid: self._users[user.uid]
            for user in self.get_users()
            if predicate(user)
        }

        friends = {
            user_id: [
                friend_id
                for friend_id in self._friends[user_id]
                if friend_id in users
            ]
            for user_id in users
        }

        subscriptions = {
            user_id: self._subscriptions[user_id]
            for user_id in users
        }

        members = {}
        for group_id, members_list in self._members.items():
            pack = [member for member in members_list if member in users]
            if pack:
                members[group_id] = pack

        groups = {group_id: self._groups[group_id] for group_id in members}

        user_attributes = {
            user_id: self._user_attributes[user_id]
            for user_id in users
        }

        group_attributes = {
            group_id: self._group_attributes[group_id]
            for group_id in groups
        }

        cities = self._cities
        universities = self._universities

        return Community(
            users=users,
            groups=groups,
            members=members,
            subscriptions=subscriptions,
            friends=friends,
            user_attributes=user_attributes,
            group_attributes=group_attributes,
            cities=cities,
            universities=universities,
        )

    def get_groups(self):
        """Get list of group objects.

        Returns:
            Sequence of Community.Group objects.
        """
        for group_id in self._group:
            yield self.get_group(group_id)

    def get_users(self):
        """Get list of user objects.

        Returns:
            Sequence of Community.User objects.
        """
        for user_id in self._users:
            yield self.get_user(user_id)
            
    def get_user(self, uid):
        """Get user with given id.

        Args:
            uid: user's id.

        Returns:
            Community.User object.
        """
        return Community.User(self, uid)
    
    def get_group(self, uid):
        """Get group with given id.

        Args:
            uid: group's id.

        Returns:
            Community.Group object.
        """
        return Community.Group(self, uid)

    def get_edgelist(self):
        """Get sequence of edges of community graph.

        Returns:
            Sequence of pairs of Community.User objects.
            For each pair of friends {u, v},
            there are entries (u, v) and (v, u).
        """
        for user in self.get_users():
            for friend in user.friends:
                yield (user, friend)

    def get_users_table(self):
        """Get pandas DataFrame with users.

        Returns:
            DataFrame object.
        """
        return pd.DataFrame.from_items(
            items=(
                (user.uid, (
                    user.name, user.age, user.city, user.university,
                    user.last_seen, len(user.friends), len(user.groups),
                ))
                for user in self.get_users()
            ),
            columns=['Name', 'Age', 'City', 'University',
                     'Last Seen', 'Number of friends', 'Number of groups'],
            orient='index',
        )

    def friends_graph(self):
        """Converts community to NetworkX graph using Community.User objects as
        node labels.

        Returns:
            networkx.Graph object.
        """
        g = nx.Graph()
        g.add_nodes_from(self.get_users())
        g.add_edges_from(self.get_edgelist())

        return g

    def plot_geodata(self, embed=False):
        """Plot users on the map.

        Args:
            embed: True if map should be drawn in IPython Notebook cell.
        """
        counter = Counter(u.city_id for u in self.get_users())
        data = []
        for city_id, count in counter.items():
            if np.isnan(city_id):
                continue
            name, lat, lon = self._cities[city_id]
            if (lat, lon) != (None, None):
                data.append((lon, lat, count * 3))
        xs, ys, sizes = list(zip(*data))
        plt.scatter(xs, ys, s=sizes)
        if embed:
            return mplleaflet.display()
        else:
            return mplleaflet.show()

