# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import shutil
import subprocess

REPO_DIR = os.path.dirname(os.path.dirname(__file__))


def test_pre_commit_hook(tmpdir):
    # XXX: We need to create a new repo and copy the real repo in there as running
    # pre-commit with the real repo fails on CI (git checkout failure).
    tmp_repo_dir = os.path.join(tmpdir, "tyv")
    shutil.copytree(REPO_DIR, tmp_repo_dir)
    shutil.rmtree(os.path.join(tmp_repo_dir, ".git"))

    cwd = os.getcwd()
    os.chdir(tmp_repo_dir)

    subprocess.run(["git", "init"], check=True)
    subprocess.run(["git", "config", "user.email", "pinco@pallino"], check=True)
    subprocess.run(["git", "config", "user.name", "Pinco Pallino"], check=True)
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "commit", "-m", "all"], check=True)

    os.chdir(cwd)

    proc = subprocess.run(
        [
            "pre-commit",
            "try-repo",
            tmp_repo_dir,
            "taskcluster_yml",
            "--verbose",
            "--all-files",
        ],
        check=True,
        capture_output=True,
    )

    assert any(
        b"taskcluster_yml" in line and b"Passed" in line
        for line in proc.stdout.splitlines()
    )
