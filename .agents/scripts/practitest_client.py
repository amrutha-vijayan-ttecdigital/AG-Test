#!/usr/bin/env python3
"""
PractiTest API client.

Loads creds from .env (PRACTITEST_API_KEY, PRACTITEST_PROJECT_ID,
PRACTITEST_FILTER_ID). Provides paginated list / get / search /
create-run helpers. PractiTest uses HTTP basic auth where the
"username" is the developer email and the "password" is the API token.

Usage from Python:
    from practitest_client import PractiTestClient
    pt = PractiTestClient.from_env()
    tests = pt.list_tests(filter_id=pt.filter_id)
    print(f'{len(tests)} tests in filter')

Usage from CLI:
    python3 .agents/scripts/practitest_client.py ls
    python3 .agents/scripts/practitest_client.py show 22694087
    python3 .agents/scripts/practitest_client.py search "balance"
    python3 .agents/scripts/practitest_client.py runs --test-id 22694087
    python3 .agents/scripts/practitest_client.py push-result \
        --test-id 22694087 --status PASSED --note "auto-replay run"
"""
import argparse, base64, json, os, sys, time, urllib.parse, urllib.request


def _load_env(path=".env"):
    """Read a .env file and merge into os.environ if not already set."""
    if not os.path.exists(path):
        # try parent dir
        parent = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        if os.path.exists(parent):
            path = parent
        else:
            return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip("'").strip('"')
            os.environ.setdefault(k, v)


class PractiTestError(Exception):
    pass


class PractiTestClient:
    BASE = "https://api.practitest.com/api/v2"

    def __init__(self, api_key, project_id, email, filter_id=None):
        self.api_key = api_key
        self.project_id = str(project_id)
        self.email = email
        self.filter_id = str(filter_id) if filter_id else None
        creds = f"{email}:{api_key}".encode()
        self._auth = "Basic " + base64.b64encode(creds).decode()

    @classmethod
    def from_env(cls):
        _load_env()
        api_key = os.environ.get("PRACTITEST_API_KEY")
        project_id = os.environ.get("PRACTITEST_PROJECT_ID")
        filter_id = os.environ.get("PRACTITEST_FILTER_ID")
        # PractiTest uses email as the "username" in basic auth.
        email = os.environ.get(
            "PRACTITEST_EMAIL", "your-email@domain.com"
        )
        if not api_key or not project_id:
            raise PractiTestError(
                "PRACTITEST_API_KEY and PRACTITEST_PROJECT_ID must be set in .env"
            )
        return cls(api_key, project_id, email, filter_id=filter_id)

    # PractiTest rate-limit is 30 requests / 60 seconds — throttle to ~25/min
    # so we never trip the limiter on full filter pulls.
    _RATE_INTERVAL = 2.5
    _last_call = 0.0

    def _req(self, method, path, params=None, body=None, _retries=2):
        # Simple monotonic throttle
        gap = time.monotonic() - PractiTestClient._last_call
        if gap < self._RATE_INTERVAL:
            time.sleep(self._RATE_INTERVAL - gap)
        PractiTestClient._last_call = time.monotonic()

        qs = ""
        if params:
            # PractiTest uses kebab-case query params (e.g., filter-id)
            qs = "?" + urllib.parse.urlencode(params)
        url = f"{self.BASE}{path}{qs}"
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, method=method, data=data, headers={
            "Authorization": self._auth,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:400]
            # On 429, honor Retry-After (or fall back to 60s) and retry once.
            if e.code == 429 and _retries > 0:
                retry_after = 60
                try:
                    retry_after = int(e.headers.get("Retry-After", "60"))
                except (TypeError, ValueError):
                    pass
                print(f"  [PT 429] sleeping {retry_after}s then retrying {path}", file=sys.stderr)
                time.sleep(retry_after + 1)
                return self._req(method, path, params=params, body=body, _retries=_retries - 1)
            raise PractiTestError(f"{method} {url} → {e.code}: {body}") from e

    def _paginate(self, path, params=None, page_size=100, max_pages=20):
        out = []
        page = 1
        while page <= max_pages:
            p = dict(params or {}, **{"page[number]": page, "page[size]": page_size})
            data = self._req("GET", path, params=p)
            batch = data.get("data", []) or []
            out.extend(batch)
            meta = data.get("meta") or {}
            next_page = meta.get("next-page")
            if not next_page:
                break
            page = next_page
        return out

    # ── Tests ─────────────────────────────────────────────────────────────
    def list_tests(self, filter_id=None, max_pages=20):
        params = {}
        fid = filter_id or self.filter_id
        if fid:
            params["filter-id"] = fid
        return self._paginate(
            f"/projects/{self.project_id}/tests.json",
            params=params, max_pages=max_pages,
        )

    def get_test(self, test_id):
        d = self._req("GET", f"/projects/{self.project_id}/tests/{test_id}.json")
        return d.get("data", {})

    def search_tests(self, keyword, filter_id=None, max_pages=20):
        """Return tests whose name OR description contains keyword (case-insensitive)."""
        all_tests = self.list_tests(filter_id=filter_id, max_pages=max_pages)
        kw = keyword.lower()
        out = []
        for t in all_tests:
            attrs = t.get("attributes", {}) or {}
            hay = " ".join(str(attrs.get(k, "")) for k in ("name", "description", "tags"))
            if kw in hay.lower():
                out.append(t)
        return out

    def list_test_steps(self, test_id):
        # PractiTest exposes steps via the project-level /steps.json endpoint
        # filtered by test-ids — there's no nested /tests/{id}/steps.json route.
        return self._paginate(
            f"/projects/{self.project_id}/steps.json",
            params={"test-ids": str(test_id)},
            max_pages=10,
        )

    # ── Test sets / instances / runs ──────────────────────────────────────
    def list_sets(self, filter_id=None, max_pages=10):
        params = {}
        if filter_id: params["filter-id"] = str(filter_id)
        return self._paginate(
            f"/projects/{self.project_id}/sets.json",
            params=params, max_pages=max_pages,
        )

    def list_instances(self, set_id=None, test_id=None, filter_id=None, max_pages=10):
        params = {}
        if set_id: params["set-ids"] = str(set_id)
        if test_id: params["test-ids"] = str(test_id)
        if filter_id: params["filter-id"] = str(filter_id)
        return self._paginate(
            f"/projects/{self.project_id}/instances.json",
            params=params, max_pages=max_pages,
        )

    def list_runs(self, test_id=None, instance_id=None, max_pages=10):
        params = {}
        if test_id: params["test-ids"] = str(test_id)
        if instance_id: params["instance-ids"] = str(instance_id)
        return self._paginate(
            f"/projects/{self.project_id}/runs.json",
            params=params, max_pages=max_pages,
        )

    def create_run(self, instance_id, status="PASSED", run_steps=None, custom_fields=None,
                   note=None, exit_code=0, run_duration=None):
        """Create a run against a test instance.

        instance_id: PractiTest instance (a test in a set), NOT a raw test_id.
        status: PASSED / FAILED / BLOCKED / N/A / NO RUN

        Presence of `automated-execution-output` (set from `note`) is what marks
        the run as automated in PractiTest — there's no separate boolean flag.
        """
        attrs = {
            "instance-id": int(instance_id),
            "exit-code": exit_code,
            "automated-execution-output": note or "",
        }
        if run_duration is not None:
            attrs["run-duration"] = run_duration
        if run_steps:
            attrs["steps"] = run_steps
        else:
            # Single rolled-up step
            attrs["steps"] = [{
                "name": "Automated run",
                "actual-results": note or "",
                "status": status,
            }]
        if custom_fields:
            attrs["custom-fields"] = custom_fields
        body = {"data": {"type": "instances", "attributes": attrs}}
        d = self._req("POST", f"/projects/{self.project_id}/runs.json", body=body)
        return d.get("data", {})


# ─── CLI ──────────────────────────────────────────────────────────────────
def cmd_ls(args, pt):
    tests = pt.list_tests(filter_id=args.filter or pt.filter_id)
    print(f"{len(tests)} tests in filter {args.filter or pt.filter_id}")
    for t in tests[: args.limit]:
        a = t.get("attributes", {})
        run_status = a.get("run-status", "?")
        print(f"  [{t['id']:>9s}]  {run_status:>10s}  #{a.get('display-id','?'):>4}  {a.get('name','')[:90]}")


def cmd_show(args, pt):
    t = pt.get_test(args.test_id)
    a = t.get("attributes", {})
    print(f"Test {t.get('id')}  #{a.get('display-id')}  {a.get('name','')}")
    print(f"  run-status: {a.get('run-status')}  status: {a.get('status')}")
    print(f"  description: {(a.get('description') or '')[:200]}")
    print(f"  preconditions: {(a.get('preconditions') or '')[:200]}")
    cf = a.get("custom-fields") or {}
    if cf:
        print("  custom-fields:")
        for k, v in cf.items():
            print(f"    {k} = {str(v)[:80]}")


def cmd_search(args, pt):
    hits = pt.search_tests(args.keyword, filter_id=args.filter or pt.filter_id)
    print(f"{len(hits)} matches for {args.keyword!r}")
    for t in hits[: args.limit]:
        a = t.get("attributes", {})
        print(f"  [{t['id']:>9s}]  {a.get('run-status','?'):>10s}  #{a.get('display-id','?'):>4}  {a.get('name','')[:90]}")


def cmd_runs(args, pt):
    runs = pt.list_runs(test_id=args.test_id)
    print(f"{len(runs)} runs for test {args.test_id}")
    for r in runs[: args.limit]:
        a = r.get("attributes", {})
        print(f"  [{r['id']:>9s}]  {a.get('run-status','?'):>10s}  by {a.get('run-by','?')}  on {a.get('updated-at','')[:19]}")


def cmd_steps(args, pt):
    steps = pt.list_test_steps(args.test_id)
    print(f"{len(steps)} steps for test {args.test_id}")
    for s in steps:
        a = s.get("attributes", {})
        print(f"  {a.get('position','?')}. {a.get('name','')[:80]}")
        ex = (a.get("expected-results") or "").strip()
        if ex: print(f"     expected: {ex[:100]}")


def cmd_push_result(args, pt):
    if not args.instance_id and not args.test_id:
        print("ERROR: --instance-id or --test-id required", file=sys.stderr)
        sys.exit(1)
    instance_id = args.instance_id
    if not instance_id:
        # Try to find an instance for the test
        inst = pt.list_instances(test_id=args.test_id, max_pages=2)
        if not inst:
            print(f"ERROR: no instance found for test {args.test_id}. Add it to a Test Set first.", file=sys.stderr)
            sys.exit(1)
        instance_id = inst[0]["id"]
        print(f"Using first instance {instance_id} for test {args.test_id}")
    run = pt.create_run(
        instance_id=instance_id,
        status=args.status,
        note=args.note or "",
    )
    print(f"Created run {run.get('id')} status={args.status}")


def main():
    ap = argparse.ArgumentParser(description="PractiTest CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ls", help="List tests in the configured filter")
    p.add_argument("--filter", default=None, help="Filter ID (default from .env)")
    p.add_argument("--limit", type=int, default=200)
    p.set_defaults(fn=cmd_ls)

    p = sub.add_parser("show", help="Show a single test")
    p.add_argument("test_id")
    p.set_defaults(fn=cmd_show)

    p = sub.add_parser("steps", help="List steps for a test")
    p.add_argument("test_id")
    p.set_defaults(fn=cmd_steps)

    p = sub.add_parser("search", help="Keyword search inside the filter")
    p.add_argument("keyword")
    p.add_argument("--filter", default=None)
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(fn=cmd_search)

    p = sub.add_parser("runs", help="List runs for a test")
    p.add_argument("--test-id", required=True)
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(fn=cmd_runs)

    p = sub.add_parser("push-result", help="Create a run against an instance")
    p.add_argument("--instance-id", default=None, help="PractiTest instance ID (preferred)")
    p.add_argument("--test-id", default=None, help="Test ID — looks up first instance")
    p.add_argument("--status", default="PASSED", choices=("PASSED","FAILED","BLOCKED","N/A","NO RUN"))
    p.add_argument("--note", default="")
    p.set_defaults(fn=cmd_push_result)

    args = ap.parse_args()
    try:
        pt = PractiTestClient.from_env()
    except PractiTestError as ex:
        print(f"ERROR: {ex}", file=sys.stderr)
        sys.exit(1)
    args.fn(args, pt)


if __name__ == "__main__":
    main()
