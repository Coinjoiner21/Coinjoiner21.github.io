# Coordinator changes required for the Coinjoiner status site

The status pages at `/status/` and `/status_testnet/` rely on three things from
the coordinator that vanilla WalletWasabi does **not** ship with. Apply the
patches below to your coordinator fork, rebuild, and redeploy.

## 1. Expose `GET /wabisabi/coinjoin-history`

The site reads coinjoin history from this endpoint. It serves a JSON file that
the watcher script (step 2) maintains on disk.

In `WalletWasabi.Coordinator/Controllers/WabiSabiController.cs`:

- Add `using System.IO;` to the top of the file.
- Paste the `GetCoinJoinHistory()` method from
  [`coinjoin-history-endpoint.cs`](./coinjoin-history-endpoint.cs) right after
  the existing `GetHumanMonitor()` method.

The endpoint returns `[]` if the history file does not yet exist, so it is safe
to deploy before the watcher has produced any output.

## 2. Run the history watcher

The endpoint above only reads `coinjoin-history.json`; it never writes it. The
watcher in [`coinjoin-history-watcher.py`](./coinjoin-history-watcher.py) tails
the coordinator's `Logs.txt`, picks out successful broadcasts, and appends them
to that JSON file.

- Verify the paths at the top of the script match your install (default is
  `~/.walletwasabi/coordinator/`).
- Run it as a long-lived process. Example systemd unit:

  ```ini
  [Unit]
  Description=Coinjoiner history watcher
  After=network.target

  [Service]
  ExecStart=/usr/bin/python3 /opt/coinjoiner/coinjoin-history-watcher.py
  Restart=always
  User=<coordinator-user>

  [Install]
  WantedBy=multi-user.target
  ```

Notes:
- The script trusts the log line format
  `Successfully broadcast the coinjoin: <txid>`. If a future coordinator release
  changes that wording, the regex breaks silently — re-test after every
  upgrade.
- `coinjoin-history.json` is rewritten in full on every new entry. Fine at
  current volumes; revisit if you ever reach hundreds of thousands of rounds.
- Only coinjoins present in the *current* log are picked up. To backfill
  history, concatenate rotated logs into a temp file and run the script against
  it once.

## 3. Enable CORS on the coordinator

Browsers refuse the API responses with `Access-Control-Allow-Origin missing`
unless the coordinator emits CORS headers. Vanilla WalletWasabi has no CORS
middleware registered.

In `WalletWasabi.Coordinator/Startup.cs`:

**`ConfigureServices` — register the policy** (anywhere in the method):

```csharp
services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
        policy.AllowAnyOrigin()
              .AllowAnyHeader()
              .AllowAnyMethod());
});
```

**`Configure` — wire the middleware between `UseRouting` and `UseEndpoints`:**

```csharp
public void Configure(IApplicationBuilder app, IWebHostEnvironment env)
{
    app.UseRouting();
    app.UseCors();              // <-- added
    app.UseResponseCompression();
    app.UseEndpoints(endpoints => endpoints.MapControllers());
    app.UseRequestTimeouts();
}
```

`AllowAnyOrigin()` is appropriate because the exposed endpoints
(`human-monitor`, `coinjoin-history`) are public and read-only. If a future
endpoint uses cookies or auth, switch to a specific origin list —
`AllowAnyOrigin` is incompatible with `AllowCredentials` per the CORS spec.

## Verifying

After redeploying, from any machine:

```sh
curl -is -H "Origin: https://coinjoiner.com" \
  https://api.coinjoiner.com/wabisabi/coinjoin-history | head -n 20
```

Expect:
- HTTP `200` with a JSON body (`[]` if the watcher hasn't seen a coinjoin yet),
- a response header `Access-Control-Allow-Origin: *`.

Repeat against `https://testnet.coinjoiner.com/...` for the testnet
coordinator. Once both succeed, both status pages will flip from "Offline" to
"Online".
