# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import functools

import jsone
import jsonschema
import referencing
import referencing.jsonschema
import requests
import slugid
import yaml
from requests.adapters import HTTPAdapter, Retry

from taskcluster_yml_validator.events import pull_request_open, push, tag_push

TASKCLUSTER_YML_SCHEMA_URL = "https://community-tc.services.mozilla.com/schemas/github/v1/taskcluster-github-config.v1.json"
TASK_SCHEMA_URL = "https://community-tc.services.mozilla.com/schemas/queue/v1/create-task-request.json"

# TODO: Instead of trying all possible payload schemas, use the worker manager API to figure out
# exactly which one is the right one. We can do this after https://bugzilla.mozilla.org/show_bug.cgi?id=1609099
# is fixed.
PAYLOAD_SCHEMA_URLS = [
    "https://community-tc.services.mozilla.com/schemas/docker-worker/v1/payload.json",
    "https://community-tc.services.mozilla.com/schemas/generic-worker/multiuser_posix.json",
    "https://community-tc.services.mozilla.com/schemas/generic-worker/multiuser_windows.json",
    "https://community-tc.services.mozilla.com/schemas/generic-worker/insecure_posix.json",
]

# The schemas are downloaded from a live Taskcluster deployment, so a transient
# failure there should not fail the validation.
session = requests.Session()
session.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
        )
    ),
)


@functools.lru_cache(maxsize=None)
def get_schema(url):
    """Download a schema, keeping it around so it is only downloaded once."""
    r = session.get(url)
    r.raise_for_status()
    return r.json()


@functools.lru_cache(maxsize=None)
def retrieve_resource(uri):
    """Resolve a remote reference through the caching schema downloader."""
    return referencing.Resource.from_contents(
        get_schema(uri),
        default_specification=referencing.jsonschema.DRAFT202012,
    )


# The registry is needed to cache the resolved references, so that each schema
# is only downloaded once.
registry = referencing.Registry(retrieve=retrieve_resource)


@functools.lru_cache(maxsize=None)
def get_validator(url):
    """Build a reusable validator for the schema at the given URL."""
    schema = get_schema(url)
    validator_class = jsonschema.validators.validator_for(schema)
    validator_class.check_schema(schema)
    return validator_class(schema, registry=registry)


def validate_instance(validator, instance):
    """Validate an instance, raising the most relevant error on failure."""
    error = jsonschema.exceptions.best_match(validator.iter_errors(instance))
    if error is not None:
        raise error


def validate(path):
    with open(path, "r") as f:
        taskcluster_yml = yaml.safe_load(f.read())

    validate_instance(get_validator(TASKCLUSTER_YML_SCHEMA_URL), taskcluster_yml)

    def as_slugid(tid):
        return slugid.nice()

    events = [push, tag_push, pull_request_open]

    task_validator = get_validator(TASK_SCHEMA_URL)

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
            if not isinstance(task, dict):
                raise TypeError(
                    f"Task should be of dict type (after json-e parsing). Found: {type(task).__name__}"
                )

            # According to https://docs.taskcluster.net/docs/reference/integrations/github/taskcluster-yml-v1#result, the tasks
            # will be passed to createTask directly after removing "taskId", so we can validate with the create-task-request schema.
            if "taskId" in task:
                del task["taskId"]

            validate_instance(task_validator, task)

            payload_validation_err = None
            for payload_schema_url in PAYLOAD_SCHEMA_URLS:
                try:
                    validate_instance(
                        get_validator(payload_schema_url), task["payload"]
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
