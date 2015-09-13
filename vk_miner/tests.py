# Copyright 2015 Artur Chakhvadze. All Rights Reserved.

"""Tests."""

__author__ = 'Artur Chakhvadze (norpadon@yandex.ru)'

import os
import sys

import unittest
import vk_async
import vk_miner.community
import vk_miner.algorithms

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Copy to test_props.py and fill it.
MY_ID = 170100773
APP_IDS = [] # API/Client id.
USER_LOGIN = ''
USER_PASSWORD = ''

from test_props import APP_IDS, USER_LOGIN, USER_PASSWORD, MY_ID

class CommunityTestCase(unittest.TestCase):
    pass

class VkMinerTestCase(unittest.TestCase):
    def setUp(self):
        self.api = vk_async.API(
            app_ids=APP_IDS,
            user_login=USER_LOGIN,
            user_password=USER_PASSWORD
        )

    def test_loading(self):
        friends = vk_miner.algorithms.load_friends_bfs(self.api, [MY_ID], 2)
        self.assertFalse(friends.users.empty)

if __name__ == '__main__':
    unittest.main()
