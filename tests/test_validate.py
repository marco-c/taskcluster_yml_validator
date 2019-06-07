# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os

from taskcluster_yml_validator import validate

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def test_get_qaneeded_labels():
    validate(os.path.join(FIXTURES_DIR, "bugbug.taskcluster.yml"))
