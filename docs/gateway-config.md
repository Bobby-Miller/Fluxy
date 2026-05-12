# Gateway Config

Fluxy can generate a narrow Gateway configuration resource for a SQLite database connection. The canonical module is `fluxy.gateway_config`.

Create the local test database:

```bash
uv run python - <<'PY'
import sqlite3

connection = sqlite3.connect("hello.sqlite3")
try:
    connection.execute("create table if not exists hello (id integer primary key, message text not null)")
    connection.execute("delete from hello")
    connection.execute("insert into hello (message) values (?)", ("Hello from SQLite",))
    connection.commit()
finally:
    connection.close()
PY
```

Deploy the Gateway config resource:

```bash
uv run python -m fluxy.gateway_config \
  /usr/local/bin/ignition/data \
  hello.sqlite3 \
  --connection-name FluxyHello
```

This writes:

```text
/usr/local/bin/ignition/data/udb/hello.sqlite3
/usr/local/bin/ignition/data/config/resources/core/ignition/database-connection/FluxyHello/config.json
/usr/local/bin/ignition/data/config/resources/core/ignition/database-connection/FluxyHello/resource.json
```

The generated connection uses:

```text
driver: SQLite
translator: SQLITE
connectURL: jdbc:sqlite:${data}/udb/hello.sqlite3
```

Important constraints:

`fluxy.gateway_config` writes Gateway resources, not project resources. `fx.project.request_scan()` does not reload these resources. Ignition did not hot-load this connection in local testing; restart the Gateway or use the Gateway UI/config import path.

Do not edit `data/db/config.idb` directly for this workflow. Ignition 8.3 stores file-backed Gateway config resources under `data/config/resources/`, and direct database edits are a brittle last resort.
