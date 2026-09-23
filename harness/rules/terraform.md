---
paths:
  - "**/*.tf"
  - "**/*.tfvars.example"
  - "**/*.tf.json"
  - "**/.terraform.lock.hcl"
---

# Terraform Conventions

## fmt before done

Run `terraform fmt` (recursively, from the `terraform/` root) before considering any change complete. CI will reject unformatted files.

## Layout

```
terraform/
  modules/<provider>/      # reusable, provider-scoped
  environments/<env>/      # staging, prod — one per env
```

Provider modules are scoped per provider (e.g., one for each cloud and one for DNS). Follow the existing modules in this repo as the reference.

## DNS module is provider-independent

The DNS module is intentionally separated from compute providers so the same DNS module composes with any compute backend. Never inline DNS records into a compute module.

<!-- The reason: when compute migrates between providers, DNS records must point
     at the NEW server IP without re-creating the record (which would lose history
     and break any proxy/cache state at the DNS provider). Keeping DNS in its own
     module means terraform state for DNS survives compute changes. -->

## Variables, never literals

All provider-specific identifiers — region names, image IDs, instance types, account IDs, zone IDs — go through `variable` blocks. No bare strings in resource bodies. This keeps modules portable across environments.

## .tfvars hygiene

- NEVER commit `*.tfvars` files. They contain secrets and per-env values.
- DO commit `*.tfvars.example` with sanitized placeholders so new operators can copy and fill.
- `.gitignore` should exclude `*.tfvars`; do not add exceptions.

## State

Remote state only — never commit `terraform.tfstate*`. State backend is configured per environment under `environments/<env>/backend.tf`.
