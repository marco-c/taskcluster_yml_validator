# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse

import jsone
import jsonschema
import requests
import slugid
import yaml

from taskcluster_yml_validator.events import pull_request_open, push, tag_push


def validate(path):
    r = requests.get(
        "https://schemas.taskcluster.net/github/v1/taskcluster-github-config.v1.json"
    )
    r.raise_for_status()
    taskcluster_yml_schema = r.json()

    r = requests.get(
        "https://schemas.taskcluster.net/queue/v1/create-task-request.json"
    )
    r.raise_for_status()
    task_schema = r.json()

    # TODO: Don't assume docker-worker!
    r = requests.get("https://schemas.taskcluster.net/docker-worker/v1/payload.json")
    r.raise_for_status()
    payload_schema = r.json()

    with open(path, "r") as f:
        taskcluster_yml = yaml.safe_load(f.read())

    jsonschema.validate(instance=taskcluster_yml, schema=taskcluster_yml_schema)

    def as_slugid(tid):
        return slugid.nice()

    events = [push, tag_push, pull_request_open]

    for event in events:
        rendered_taskcluster_yml = jsone.render(
            taskcluster_yml,
            context={
                "tasks_for": event.tasks_for,
                "as_slugid": as_slugid,
                "event": event.event,
            },
        )

        for task in rendered_taskcluster_yml["tasks"]:
            # According to https://docs.taskcluster.net/docs/reference/integrations/github/taskcluster-yml-v1#result, the tasks
            # will be passed to createTask directly after removing "taskId", so we can validate with the create-task-request schema.
            if "taskId" in task:
                del task["taskId"]

            jsonschema.validate(instance=task, schema=task_schema)
            jsonschema.validate(instance=task["payload"], schema=payload_schema)


def main():
    description = "Validate a .taskcluster.yml file"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("tcml", help="Path to a .taskcluster.yml file")
    args = parser.parse_args()

    validate(args.tcml)
