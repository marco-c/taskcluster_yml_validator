# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse

import jsone
import yaml

from taskcluster_yml_validator.events import pull_request_open, push, tag_push


def validate(path):
    with open(path, "r") as f:
        taskcluster_yml = yaml.load(f.read())

    def as_slugid(tid):
        return tid

    events = [push, tag_push, pull_request_open]

    for event in events:
        jsone.render(
            taskcluster_yml,
            context={
                "tasks_for": event.tasks_for,
                "as_slugid": as_slugid,
                "event": event.event,
            },
        )


def main():
    description = "Validate a .taskcluster.yml file"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("tcml", help="Path to a .taskcluster.yml file")
    args = parser.parse_args()

    validate(args.tcml)
