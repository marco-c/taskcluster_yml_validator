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
        "https://community-tc.services.mozilla.com/schemas/github/v1/taskcluster-github-config.v1.json"
    )
    r.raise_for_status()
    taskcluster_yml_schema = r.json()

    r = requests.get(
        "https://community-tc.services.mozilla.com/schemas/queue/v1/create-task-request.json"
    )
    r.raise_for_status()
    task_schema = r.json()

    # TODO: Instead of trying all possible payload schemas, use the worker manager API to figure out
    # exactly which one is the right one. We can do this after https://bugzilla.mozilla.org/show_bug.cgi?id=1609099
    # is fixed.
    payload_schema_urls = [
        "https://raw.githubusercontent.com/taskcluster/taskcluster/3ed511ef9119da54fc093e976b7b5955874c9b54/workers/docker-worker/schemas/v1/payload.json",
        "https://community-tc.services.mozilla.com/schemas/generic-worker/docker_posix.json",
        "https://community-tc.services.mozilla.com/schemas/generic-worker/multiuser_posix.json",
        "https://community-tc.services.mozilla.com/schemas/generic-worker/multiuser_windows.json",
        "https://community-tc.services.mozilla.com/schemas/generic-worker/simple_posix.json",
    ]

    payload_schemas = {}

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
                "taskcluster_root_url": "https://tc.mozilla.com",
                "tasks_for": event.tasks_for,
                "as_slugid": as_slugid,
                "event": event.event,
            },
        )

        if "tasks" not in rendered_taskcluster_yml:
            continue

        for task in rendered_taskcluster_yml["tasks"]:
            # According to https://docs.taskcluster.net/docs/reference/integrations/github/taskcluster-yml-v1#result, the tasks
            # will be passed to createTask directly after removing "taskId", so we can validate with the create-task-request schema.
            if "taskId" in task:
                del task["taskId"]

            jsonschema.validate(instance=task, schema=task_schema)

            payload_validation_err = None
            for payload_schema_url in payload_schema_urls:
                if payload_schema_url not in payload_schemas:
                    r = requests.get(payload_schema_url)
                    r.raise_for_status()
                    payload_schemas[payload_schema_url] = r.json()

                try:
                    jsonschema.validate(
                        instance=task["payload"],
                        schema=payload_schemas[payload_schema_url],
                    )
                    payload_validation_err = None
                    break
                except jsonschema.exceptions.ValidationError as e:
                    if payload_validation_err is None:
                        payload_validation_err = e

            if payload_validation_err is not None:
                raise payload_validation_err


def main():
    description = "Validate a .taskcluster.yml file"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("tcml", help="Path to a .taskcluster.yml file")
    args = parser.parse_args()

    validate(args.tcml)
