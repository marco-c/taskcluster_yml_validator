# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import re
import urllib.request

import jsone
import jsonschema
import pytest

import taskcluster_yml_validator
from taskcluster_yml_validator import validate

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def uncached_schemas():
    """Forget the downloaded schemas, so that downloads can be observed."""
    for cached in (
        taskcluster_yml_validator.get_schema,
        taskcluster_yml_validator.retrieve_resource,
        taskcluster_yml_validator.get_validator,
    ):
        cached.cache_clear()


def test_valid_taskcluster_yml():
    validate(os.path.join(FIXTURES_DIR, "bugbug.taskcluster.yml"))


def test_valid_taskcluster_yml_with_taskcluster_root_url_context():
    validate(os.path.join(FIXTURES_DIR, "task-boot.taskcluster.yml"))


def test_invalid_taskcluster_yml():
    with pytest.raises(
        jsone.shared.InterpreterError,
        match=re.escape(
            "InterpreterError at template.tasks[8].payload.command[2]: unknown context value tag"
        ),
    ):
        validate(os.path.join(FIXTURES_DIR, "bugbug_invalid.taskcluster.yml"))


def test_invalid_main_schema_taskcluster_yml():
    with pytest.raises(
        jsonschema.exceptions.ValidationError,
        match=re.escape("'version' is a required property"),
    ):
        validate(
            os.path.join(FIXTURES_DIR, "bugbug_invalid_main_schema.taskcluster.yml")
        )


def test_invalid_schema_taskcluster_yml():
    with pytest.raises(
        jsonschema.exceptions.ValidationError,
        match=re.escape("'metadata' is a required property"),
    ):
        validate(os.path.join(FIXTURES_DIR, "bugbug_invalid_schema.taskcluster.yml"))


def test_invalid_schema_payload_taskcluster_yml():
    with pytest.raises(
        jsonschema.exceptions.ValidationError,
        match=re.escape("'python3 run.py' is not of type 'array'"),
    ):
        validate(
            os.path.join(FIXTURES_DIR, "bugbug_invalid_schema_payload.taskcluster.yml")
        )


def test_invalid_schema_task_list_taskcluster_yml():
    with pytest.raises(
        TypeError,
        match=re.escape(
            "Task should be of dict type (after json-e parsing). Found: str"
        ),
    ):
        validate(
            os.path.join(
                FIXTURES_DIR, "bugbug_invalid_schema_task_list.taskcluster.yml"
            )
        )


def test_valid_taskcluster_yml_with_win_generic_worker():
    validate(os.path.join(FIXTURES_DIR, "win.taskcluster.yml"))


def test_valid_taskcluster_yml_with_no_tasks():
    validate(os.path.join(FIXTURES_DIR, "no_tasks_on_condition.taskcluster.yml"))


def test_each_schema_is_downloaded_only_once(uncached_schemas, monkeypatch):
    downloaded = []
    real_get = taskcluster_yml_validator.session.get

    def get(url, *args, **kwargs):
        downloaded.append(url)
        return real_get(url, *args, **kwargs)

    monkeypatch.setattr(taskcluster_yml_validator.session, "get", get)

    validate(os.path.join(FIXTURES_DIR, "bugbug.taskcluster.yml"))

    assert downloaded, "no schema was downloaded at all"
    assert sorted(downloaded) == sorted(
        set(downloaded)
    ), f"some schemas were downloaded more than once: {downloaded}"


def test_references_are_not_retrieved_by_jsonschema(uncached_schemas, monkeypatch):
    # jsonschema resolves remote references with an uncached request each, which
    # is both slow and flaky, so everything has to go through our own registry.
    def urlopen(*args, **kwargs):
        raise AssertionError("jsonschema retrieved a remote reference by itself")

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    validate(os.path.join(FIXTURES_DIR, "bugbug.taskcluster.yml"))
