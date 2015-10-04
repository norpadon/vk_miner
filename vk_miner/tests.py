# Copyright 2015 Artur Chakhvadze. All Rights Reserved.

"""Tests."""

__author__ = 'Artur Chakhvadze (norpadon@yandex.ru)'

import os
import sys

import unittest
import vk_async.fetcher
import vk_miner.community
import vk_miner.algorithms

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Copy to test_props.py and fill it.
MY_ID = 170100773
APP_IDS = [] # API/Client id.
USER_LOGIN = ''
USER_PASSWORD = ''

from test_props import APP_IDS, USER_LOGIN, USER_PASSWORD, MY_ID, GROUP_ID

class CommunityTestCase(unittest.TestCase):
    pass

class VkMinerTestCase(unittest.TestCase):
    def setUp(self):
        self.api = vk_async.fetcher.Fetcher(
            app_ids=APP_IDS,
            username=USER_LOGIN,
            password=USER_PASSWORD
        )

    def test_loading_friends(self):
        friends = vk_miner.algorithms.load_friends_bfs(self.api, [MY_ID], 2)
        friends.save('friends.hdf5')
        self.assertFalse(friends.users.empty)

    def test_loading_group(self):
        users = vk_miner.algorithms.load_group_members(self.api, GROUP_ID)
        users.save('group.hdf5')
        self.assertFalse(users.users.empty)

if __name__ == '__main__':
    unittest.main()
