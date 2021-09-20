# taskcluster-yml-validator

**taskcluster-yml-validator** allows validating a .taskcluster.yml file against all possible GitHub events, before pushing to a GitHub repository.

Instead of pushing and seeing Taskcluster bark at you, you can be proactive and validate the .taskcluster.yml ahead of time.

## Usage

### Option 1: Through pre-commit

Add the following entry to the `repos` in your .pre-commit-config.yaml file:

```YAML
-   repo: https://github.com/marco-c/taskcluster_yml_validator
    rev: v0.0.2
    hooks:
    -   id: taskcluster_yml
```

### Option 2: Directly as a script

First, install the package using pip:

```bash
pip install --user taskcluster_yml_validator
```

Then, run it in the root directory of your repository:

```bash
taskcluster_yml_validator
```
