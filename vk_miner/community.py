# Copyright 2015 Artur Chakhvadze. All Rights Reserved.

"""Community class."""

__author__ = 'Artur Chakhvadze (norpadon@yandex.ru)'

import logging
from functools import *
from collections import Counter

import pandas as pd
import numpy as np
import networkx as nx
from matplotlib import pyplot as plt
import mplleaflet

logger = logging.getLogger('vk_miner')


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
            if self.uid not in self.owner.friends:
                return ()
            result = self.owner.friends.loc[self.uid]
            if not hasattr(result, '__len__'):
                result = (result,)
            return [Community.User(self.owner, uid) for uid in result]
        
        @property
        def groups(self):
            if self.uid not in self.owner.subscriptions:
                return ()
            result = self.owner.subscriptions.loc[self.uid]
            if not hasattr(result, '__len__'):
                result = (result,)
            return [Community.Group(self.owner, uid) for uid in result]

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
        
        def add_friends(self, friends):
            """Add one or more friends to user.

            Args:
                friends: Community.User object ot list of them.

            Complexity:
                O(len(community.friends)).
            """
            if not hasattr(friends, "__len__"):
                friends = [friends]
            
            us = friends + [self.uid] * len(friends)
            vs = list(us); vs.reverse()
            
            self.owner.friends = self.owner.friends.append(
                pd.Series(us, index=vs)
            )
        
        def add_groups(self, groups):
            """Add one or more subscriber to group.

            Args:
                groups: Community.Group object ot list of them.

            Complexity:
                O(len(community.subscriptions)).
            """
            if not hasattr(groups, "__len__"):
                groups = [groups]
                
            us = [self.uid] * len(groups)
                
            self.owner.subscriptions = self.owner.subscriptions.append(
                pd.Series(groups, index=us)
            )

            self.owner.members = self.owner.members.append(
                pd.Series(us, index=groups)
            )
           
        def __setattr__(self, name, value):
            if name == 'uid':
                raise AttributeError()
            if name in self.owner.users.columns:
                self.owner.users[name][self.uid] = value
            else:
                self.owner.user_attributes.loc[self.uid, name] = value
        
        def __getattr__(self, name):
            # If attribute is 'built in', take it from the users table,
            # otherwise, try to find it in attributes table.
            if name in self.owner.users.columns:
                return self.owner.users[name][self.uid]
            else:
                return self.owner.user_attributes.loc[self.uid, name]

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
        def members(self):
            if self.uid not in self.owner.members:
                return ()
            result = self.owner.members.loc[self.uid]
            if isinstance(result, int):
                result = [result]
            return [Community.User(self.owner, uid) for uid in result]
        
        def add_members(self, members):
            """Add one or more members to community.

            Args:
                members: Community.Group object ot list of them.

            Complexity:
                O(len(community.subscriptions)
            """
            if not hasattr(members, "__len__"):
                members = [members]
                
            us = [self.uid] * len(members)
                
            self.owner.members = self.owner.subscriptions.append(
                pd.Series(members, index=us)
            )

            self.owner.subscriptions = self.owner.members.append(
                pd.Series(us, index=members)
            )
           
        def __setattr__(self, name, value):
            if name == 'uid':
                raise AttributeError
            if name == 'name':
                self.owner.groups[self.uid] = value
            else:
                self.owner.group_attributes.loc[self.uid, name] = value
        
        def __getattr__(self, name):
            if name == 'name':
                return self.owner.groups[self.uid]
            else:
                return self.owner.group_attributes.loc[self.uid, name]

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
            
    def _create(self):
        """Initialize data frames and cache."""
        self.users = pd.DataFrame(
            columns=['name', 'age', 'city_id', 'university_id', 'last_seen'],
            index=pd.Index([], name='uid')
        )
        
        self.groups = pd.Series(
            name='group',
            index=pd.Index([], name='uid')
        )

        self.universities = pd.Series(
            name='university',
            index=pd.Index([], name='uid')
        )

        self.cities = pd.DataFrame(
            columns=['city', 'latitude', 'longitude'],
            index=pd.Index([], name='uid')
        )
        
        # Friends contains entries u: v, and v: u
        # for each pair of friends (u, v).
        self.friends = pd.Series()

        # Subscriptions contains entry u: g if user u is member of group g.
        self.subscriptions = pd.Series()

        # Members is inverse of subscriptions:
        # it contains entry g: u if user u is member of g.
        self.members = pd.Series()
        
        self.user_attributes = pd.Series(
            index=pd.Index([], name=['uid', 'attribute'])
        )

        self.group_attributes = pd.Series(
            index=pd.Index([], name=['uid', 'attribute'])
        )
        
    def __init__(self, filename=None, **kwargs):
        """Creates new community.

        If file is provided, load community data from it.
        Create empty community otherwise.

        Args:
            filename: path to the file with community data.
            **kwargs: values of tables.
        """
        self.fields = [
            'users', 'groups', 'cities', 'universities',
            'friends', 'members', 'subscriptions',
            'user_attributes', 'group_attributes'
        ]
        
        if filename:
            with pd.HDFStore(filename) as store:
                for field in self.fields:
                    self.__dict__[field] = store[field]
        else:
            self._create()
            for name in filter(kwargs.__contains__, self.fields):
                self.__dict__[name] = self.__dict__[name].append(kwargs[name])

        # Infer one of [members, subscriptions] from another.
        if self.members.empty:
            self.members = pd.Series(
                self.subscriptions.index,
                index=self.subscriptions
            )
        elif self.subscriptions.empty:
            self.subscriptions = pd.Series(
                self.members.index,
                index=self.members
            )

    def save(self, filename):
        """Save data to file in HDF5 format

        Args:
            filename: path to file.
        """
        with pd.HDFStore(filename) as store:
            for field in self.fields:
                store[field] = self.__dict__[field]

    def filter_users(self, predicate):
        """Get community containing all users that satisfy given predicate.

        Args:
            predicate: function from Community.User to boolean.

        Returns:
            Community object.
        """
        good_users = {
            user.uid
            for user in self.get_users_list()
            if predicate(user)
        }
        indexer = list(good_users)

        users = self.users.loc[list(good_users)]

        friends = self.friends.loc[indexer]
        friends = friends[friends.apply(good_users.__contains__)]

        subscriptions = self.subscriptions.loc[indexer]

        members = self.members[self.members.apply(good_users.__contains__)]

        groups = self.groups.loc[list(set(self.subscriptions))]

        user_attributes = self.user_attributes.sort_index()
        if not user_attributes.empty:
            user_attributes = user_attributes.loc[indexer, :]

        group_attributes = self.group_attributes.sort_index()
        if not group_attributes.empty:
            group_attributes = group_attributes.loc[groups, :]

        city_indexer = list(set(users.city_id.dropna()))
        cities = self.cities.loc[city_indexer]

        university_indexer = list(set(users.university_id.dropna()))
        universities = self.universities.loc[university_indexer]

        return Community(
            users=users,
            groups=groups,
            members=members,
            subscriptions=subscriptions,
            friends=friends,
            user_attributes=user_attributes,
            group_attributes=group_attributes,
            cities=cities,
            universities=universities
        )

    def group_list(self):
        """Get list of group objects.

        Returns:
            List of Community.Group objects.
        """
        return [self.get_group(uid) for uid in self.groups.index]

    def get_users_list(self):
        """Get list of user objects.

        Returns:
            List of Community.User objects.
        """
        return [self.get_user(uid) for uid in self.users.index]
            
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
        """Get list of edges of community graph.

        Returns:
            List of pairs of Community.User objects.
            For each pair of friends {u, v},
            there are entries (u, v) and (v, u).
        """
        ids2users = partial(map, self.get_user)
        return list(zip(ids2users(self.friends), ids2users(self.friends.index)))

    def friends_graph(self):
        """Converts community to NetworkX graph using Community.User objects as
        node labels.

        Returns:
            networkx.Graph object.
        """
        g = nx.Graph()
        g.add_nodes_from(self.get_users_list())
        g.add_edges_from(self.get_edgelist())

        return g

    def plot_geodata(self, embed=False):
        """Plot users on the map.

        Args:
            embed: True if map should be drawn in IPython Notebook cell.
        """
        counter = Counter(u.city_id for u in self.get_users_list())
        data = []
        for city_id, count in counter.items():
            if np.isnan(city_id):
                continue
            lat, lon = self.cities.loc[int(city_id)][['latitude', 'longitude']]
            if (lat, lon) != (None, None):
                data.append((lon, lat, count * 3))
        xs, ys, sizes = list(zip(*data))
        plt.scatter(xs, ys, s=sizes)
        if embed:
            return mplleaflet.display()
        else:
            return mplleaflet.show()

