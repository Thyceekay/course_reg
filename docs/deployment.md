# Zero-cost Render assessment deployment

The local Render Blueprint in `render.yaml` defines one Free web service and
one Free Render Postgres database in the same region. It does not configure a
paid plan, and this work has not created resources, deployed the app, or
authorized a purchase. Render describes Free resources as suitable for
testing and assessment, not production. Do not store important or sensitive
real-student records in this assessment deployment.

The Blueprint uses Render's Python runtime, a generated
`DJANGO_SECRET_KEY`, the internal database URL, WhiteNoise static files, and
Gunicorn. Render supplies `PORT` and `RENDER_EXTERNAL_HOSTNAME`; settings add
the Render hostname and its HTTPS origin to the host and CSRF allowlists.
Add any custom domain to `DJANGO_ALLOWED_HOSTS` and its full `https://` origin
to `DJANGO_CSRF_TRUSTED_ORIGINS`.

## Build, migration, and startup commands

The Blueprint runs:

```sh
# Build
pip install -r requirements.txt && python manage.py collectstatic --noinput

# Start (migrations run before the web process starts)
python manage.py migrate --noinput && python -m gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --access-logfile /dev/null --error-logfile -
```

Render's current Blueprint specification makes `preDeployCommand` available
only to paid web services, private services, and background workers. The Free
service therefore runs `migrate` as part of `startCommand`. It runs on every
start, including restarts and cold starts after idle spin-down, not once per
deploy. Keep migrations safe to rerun and compatible with the code currently
deployed. The Free service is limited to one instance; do not scale it or run a
second copy of this startup migration workflow concurrently. A failed
migration prevents Gunicorn from starting, but a successful schema change is
not automatically reversed if a later startup step fails.

The health check is `GET /healthz/`; it checks the database and returns only a
generic status. Production static assets are collected to `staticfiles/` and
served by WhiteNoise. Gunicorn access logging is disabled to avoid retaining
client IP addresses and request URLs; application warnings and errors go to
service logs without request bodies or credentials.

## Required environment

The Blueprint generates `DJANGO_SECRET_KEY`, sets `DJANGO_DEBUG=false`,
`DATABASE_ENGINE=postgresql`, and `DATABASE_SSL_REQUIRE=true`, and supplies
`DATABASE_URL` from the same-region Render Postgres database. Render supplies
`RENDER_EXTERNAL_HOSTNAME`. Python is pinned to 3.14.10 in the Blueprint and
`.python-version`.

For a manually configured service, provide:

| Variable | Required value |
|---|---|
| `DJANGO_SECRET_KEY` | A private random key. Do not reuse the development key or commit it. |
| `DJANGO_DEBUG` | `false` |
| `DJANGO_SECURE_SSL_REDIRECT` | Optional; defaults to the inverse of `DJANGO_DEBUG`. Set `false` only for HTTP test clients or test environments that cannot follow HTTPS redirects. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames without a scheme; Render's supplied hostname is added automatically. Add custom domains here. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated full HTTPS origins for custom domains, such as `https://courses.example.edu`. The Render hostname is added automatically. |
| `DATABASE_ENGINE` | `postgresql` |
| `DATABASE_URL` | Render Postgres internal connection URL. Prefer it when the app and database share a region. |
| `DATABASE_SSL_REQUIRE` | `true`; TLS is required for database connections. |
| `PYTHON_VERSION` | `3.14.10` (also pinned in `.python-version`). |

Render terminates HTTPS. The application trusts Render's forwarded protocol,
redirects HTTP to HTTPS, uses secure session and CSRF cookies, and enables
HSTS in non-debug mode. HSTS subdomain and preload directives remain disabled
until every subdomain under the configured host is confirmed HTTPS-only.
`SECURE_PROXY_SSL_HEADER` must only be used behind the trusted Render proxy.

The application also supports `POSTGRES_DB`, `POSTGRES_USER`,
`POSTGRES_PASSWORD`, `POSTGRES_HOST`, and optional `POSTGRES_PORT` when a
connection URL is not used. Never print, paste into a command, or commit real
database credentials.

## Create the initial live administrator

Free Render web services do not provide shell access or one-off jobs. After
the first successful deployment has run migrations, create the superuser from
a temporary local PowerShell terminal using the project's virtual environment
and the database's **external** connection URL. This connects Django locally
to the Render database; it does not create an administrator through a public
web endpoint.

If external database access has been restricted, allow the local machine's
current IP in the database's Render networking settings for this operation.
Use the full external URL and require TLS. In PowerShell, from the project
folder, enter the URL into a hidden secure-string prompt rather than putting
it in a command, script, environment file, or shell history:

```powershell
$secureDatabaseUrl = Read-Host "Render external PostgreSQL URL" -AsSecureString
$urlPointer = [IntPtr]::Zero
try {
    $urlPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureDatabaseUrl)
    $env:DATABASE_URL = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($urlPointer)
    $env:DATABASE_ENGINE = "postgresql"
    $env:DATABASE_SSL_REQUIRE = "true"
    $env:DJANGO_DEBUG = "false"
    $env:DJANGO_ALLOWED_HOSTS = "localhost"
    $env:DJANGO_SECRET_KEY = (& .\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

    .\.venv\Scripts\python.exe manage.py createsuperuser
}
finally {
    if ($urlPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($urlPointer)
    }
    $secureDatabaseUrl.Dispose()
    @(
        "DATABASE_URL",
        "DATABASE_ENGINE",
        "DATABASE_SSL_REQUIRE",
        "DJANGO_DEBUG",
        "DJANGO_ALLOWED_HOSTS",
        "DJANGO_SECRET_KEY"
    ) | ForEach-Object {
        Remove-Item "Env:$_" -ErrorAction SilentlyContinue
    }
}
```

Enter the superuser name, email, and a unique strong password only at Django's
interactive prompts; the password prompt does not echo the password. The
temporary key is generated into the process environment and is not printed.
The cleanup removes the temporary settings and clears the secure-string
buffer. Close the temporary terminal after use. Do not run `createsuperuser`
until the live database migrations have completed.

## Free-plan limitations and data persistence

These are material assessment limits, not production guarantees:

- Free Postgres has a fixed 1 GB capacity, only one Free database can be active
  per workspace, and it has no Render backups or managed connection pooling.
- A Free Postgres database expires 30 days after creation. Once expired it is
  inaccessible unless upgraded; after a further 14-day grace period Render
  deletes the database and its data. This assessment intentionally does not
  upgrade it. Export any data you are authorized to keep before expiry, and
  verify the export separately; do not rely on Render backups.
- Free web services spin down after 15 minutes without inbound traffic; a
  cold start can take about a minute. They can restart at any time and have
  ephemeral filesystems, so local files and SQLite data disappear on restart,
  redeploy, or spin-down. PostgreSQL is the only persistent application data
  store in this setup.
- A Free web service has 0.1 CPU and 512 MB RAM, cannot use persistent disks,
  shell access, one-off jobs, or multiple instances, and cannot scale beyond
  one instance.
- Free web services consume up to 750 monthly included instance hours per
  workspace while running. If the workspace exhausts those hours, all Free web
  services are suspended until the next month. Services also count against
  included bandwidth and build-pipeline minutes; overages can incur
  supplementary charges or suspend services/builds depending on payment and
  spend-limit settings. Monitor usage, do not add a payment method or upgrade
  as part of this zero-cost assessment without explicit authorization, and
  configure an appropriate spend limit if the workspace already has billing
  enabled.

The web-service filesystem is not a backup. Free Postgres has no backups, so
keep the assessment data disposable and use only synthetic or otherwise
authorized data. If a separate export is required, store it securely outside
Render and test that it can be restored; do not put database dumps or
credentials in Git.

## Rollbacks and migration limits

Render Free supports rollbacks only to the two most recent previous deploys.
A rollback restores application code, not database state or schema. Startup
migrations may already have changed the database before Gunicorn fails, and
migrations across multiple files are not one cross-migration transaction.
Use backward-compatible expand/migrate/contract changes: deploy additive
schema first, backfill separately when needed, and remove or rename fields
only after deployed code no longer depends on them. Take and verify an
authorized export before destructive schema or data changes. Never assume a
code rollback reverses a migration.

## CI and safe local production checks

GitHub Actions uses a PostgreSQL service, collects static files, runs Django
and deployment checks, checks migration consistency, explicitly runs
`PostgreSQLConcurrentRegistrationTests`, and runs the full test suite against
PostgreSQL. Its TLS setting is disabled only for the local ephemeral CI
database. The workflow has not passed on GitHub until an actual workflow run
succeeds.

For local checks, use only temporary test values; never copy live credentials.
Set a dummy `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, local
`DJANGO_ALLOWED_HOSTS`, `DATABASE_ENGINE=postgresql`,
`DATABASE_SSL_REQUIRE=true`, and a non-production test `DATABASE_URL`, then
run:

```powershell
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput
```

These checks do not prove a live PostgreSQL connection, Render configuration,
or deployment. No GitHub workflow run or Render resource creation/deployment
is claimed.

## Official guidance

- [Render: Deploy a Django app](https://render.com/docs/deploy-django)
- [Render: Blueprint specification](https://render.com/docs/blueprint-spec)
- [Render: Health checks](https://render.com/docs/health-checks)
- [Render: Free instance limitations](https://render.com/docs/free)
- [Render: Postgres connections](https://render.com/docs/postgresql-creating-connecting)
- [Render: Postgres recovery and backups](https://render.com/docs/postgresql-backups)
- [Django 5.2: Deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
- [Django 5.2: Static files deployment](https://docs.djangoproject.com/en/5.2/howto/static-files/deployment/)
