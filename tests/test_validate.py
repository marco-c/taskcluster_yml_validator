# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import re

import jsone
import pytest

from taskcluster_yml_validator import validate

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def test_valid_taskcluster_yml():
    validate(os.path.join(FIXTURES_DIR, "bugbug.taskcluster.yml"))


def test_invalid_taskcluster_yml():
    with pytest.raises(
        jsone.shared.InterpreterError,
        match=re.escape(
            "InterpreterError at template.tasks[8].payload.command[2]: unknown context value tag"
        ),
    ):
        validate(os.path.join(FIXTURES_DIR, "bugbug_invalid.taskcluster.yml"))
