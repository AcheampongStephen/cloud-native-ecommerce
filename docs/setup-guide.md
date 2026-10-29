# Windows setup

Use PowerShell in `C:\Users\Stephen\Documents\ChatGPT\DEvops`.
Python 3.13, Git, and optionally Docker Desktop with Linux containers are required.
Node is only needed for the JavaScript syntax check. WSL2/Linux concepts are
needed for the Docker engine, not for native Python execution.

```powershell
git --version
py -3.13 --version
docker version
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m commerce.manage init
docker compose up --build -d --wait --wait-timeout 180
```

The initializer generates independent credentials only when `.env` does not
exist. Existing `.env` files are preserved. Required names are in `.env.example`.
Use hexadecimal database/broker passwords if configuring manually; reserved URL
characters would require percent encoding in connection strings.

For native mode run `scripts/start.ps1`, or the explicit Python commands in
README. Use the `.venv` interpreter directly; activation is optional.
Native startup migrates and seeds before starting services. Compose does the
same for each API. Seeds insert missing catalog/stock entries and never replenish
existing stock or replace edited catalog entries.

Create an administrator interactively (never put a password in shell history):

```powershell
# Docker mode:
docker compose exec identity python -m commerce.manage admin

# Native mode:
$env:SERVICE = 'identity'
.\.venv\Scripts\python.exe -m commerce.manage admin
Remove-Item Env:SERVICE
```

The command refuses to replace an existing account. Public registration always
creates customers. Administrator tokens can update catalog and available stock.
Setting available stock is an absolute adjustment, excluding already reserved
stock; it is not an audited stock-receipt workflow.

For individual native APIs set SERVICE and run
`python -m uvicorn commerce.app:create_app --factory --host 127.0.0.1 --port PORT`
using the appropriate virtual-environment interpreter and README port mapping.

For a parallel native instance, set `$env:PORT_OFFSET = '100'` before starting
the supervisor; this uses ports 8101–8107 and matching internal URLs. Unset the
variable afterward with `Remove-Item Env:PORT_OFFSET`. This changes ports only,
not database files; do not run two native supervisors against the same data.

Dependencies are pinned transitively in `requirements.lock.txt`. To update,
resolve in a clean environment from direct `requirements.txt`, audit, test both
database backends, and regenerate the lock. Do not freeze an environment with
unrelated audit tools into the application lock.
