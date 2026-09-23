---
paths:
  - "**/ansible/**/*.{yml,yaml}"
  - "**/playbooks/**/*.{yml,yaml}"
  - "**/roles/**/*.{yml,yaml,j2}"
  - "**/group_vars/**"
  - "**/host_vars/**"
  - "**/inventory/**"
---

# Ansible Conventions

## FQCN is required

Every module call uses the fully qualified collection name. `ansible.builtin.copy`, never bare `copy`. `ansible.builtin.command`, never bare `command`. `community.docker.docker_compose_v2`, not just `docker_compose_v2`.

This rule applies in `tasks/`, `handlers/`, and inside playbooks. Follow the existing roles in this repo as the reference.

## group_vars filenames

`group_vars/<group>.yml` filenames MUST match group names in inventory **exactly**, including singular/plural and the `_` vs `-` separator.

<!-- This is a recurring footgun: inventory group `full_server` paired with file
     `full-server.yml` (hyphen) or `full_servers.yml` (plural) silently no-ops.
     Ansible doesn't warn — vars just never load. Always grep inventory for the
     exact group name and mirror it to the filename character-for-character. -->

If inventory defines a group `app_server` (singular, underscore), the file MUST be `group_vars/app_server.yml` — not `app-server.yml`, not `app_servers.yml`.

## Role layout

```
ansible/roles/<role_name>/
  tasks/main.yml
  handlers/main.yml
  defaults/main.yml
  templates/
  files/
```

When roles need to copy shared assets (e.g., compose files), reference them via a `{{ repo_root }}` variable rather than duplicating into `files/` — single source of truth.

## Task hygiene

- Every task MUST have a human-readable `name:`.
- All operations idempotent.
- Prefer builtin modules over `command:`/`shell:`. If you must use them, set `creates:` or `removes:` so re-runs are no-ops.
- Use handlers (notified, run once at end of play) for service restarts — never restart inline.
