# Nova Tools

Prefer read-only investigation first:

```bash
rg "pattern" /path
claude "<focused architecture/debug prompt>"
```

Do not expose secrets. If a secret is found, report the file/path class without
printing the value.
