# Releasing JEV Model Router

Releases are fully automated: **pushing a `v*` tag publishes the package to PyPI, builds and
pushes a Docker image, and creates a GitHub Release.** Nothing is uploaded by hand and no PyPI
API token is stored — PyPI trusts this repository's `.github/workflows/publish.yml` through
[trusted publishing](https://docs.pypi.org/trusted-publishers/). The Docker image is pushed
with the repository's own `GITHUB_TOKEN` — no extra credential either.

| | |
|---|---|
| PyPI project | [`jev-model-router`](https://pypi.org/project/jev-model-router/) |
| Docker image | [`ghcr.io/himanshu231204/jev_model_routers`](https://github.com/himanshu231204/jev_model_routers/pkgs/container/jev_model_routers) |
| PyPI workflow | [`.github/workflows/publish.yml`](.github/workflows/publish.yml) — runs on tags `v*` |
| Docker workflow | [`.github/workflows/docker.yml`](.github/workflows/docker.yml) — runs on tags `v*` |
| Version source | `src/jev_router_live/version.py` (`__version__`), read by `pyproject.toml` |
| Release notes | the version's section of [`CHANGELOG.md`](CHANGELOG.md) |

## One-time setup (already done for this repository)

1. On PyPI, a trusted publisher for `jev-model-router`: owner `himanshu231204`, repository
   `jev_model_routers`, workflow `publish.yml`, environment *(any)*.
2. On GitHub, `publish.yml` creates an environment named `pypi` on first use. Optionally add
   protection rules to it (*Settings → Environments → pypi*), e.g. required reviewers, so a
   release waits for approval before uploading.
3. `docker.yml` needs no setup: it pushes to GHCR (GitHub Container Registry) using the
   workflow's own `GITHUB_TOKEN`, scoped to `packages: write`. The first push creates the
   `ghcr.io/himanshu231204/jev_model_routers` package automatically. If you want it public
   (so `docker pull` works without logging in), set that once under the package's own
   *Package settings → Change visibility* after the first push.

## Release checklist

1. **Start from a green `main`.** CI must pass on the commit you are about to release.

2. **Pick the version** ([Semantic Versioning](https://semver.org/)):
   - `0.1.1` — bug fixes only
   - `0.2.0` — new features, backwards compatible (while `0.x`, also for breaking changes)
   - `1.0.0` — first stable release
   - pre-releases: `0.2.0rc1`, `0.2.0b1` — published to PyPI as pre-releases (pip skips them
     unless asked with `--pre`) and marked as pre-release on GitHub

3. **Bump the version** in `src/jev_router_live/version.py`:

   ```python
   __version__ = "0.2.0"
   ```

4. **Update `CHANGELOG.md`** — move the `[Unreleased]` entries under a new heading with today's
   date, leave `[Unreleased]` empty, and update the compare links at the bottom:

   ```markdown
   ## [Unreleased]

   ## [0.2.0] - 2026-10-15

   ### Added
   - …
   ```

   The heading must be exactly `## [<version>]` — the workflow fails the release if it is
   missing, and uses that section as the GitHub Release notes.

5. **Check locally**:

   ```bash
   python -m pytest -q
   pip install build twine
   python -m build && twine check --strict dist/*
   ```

6. **Merge** the version bump and changelog to `main` (via a PR, like any change).

7. **Tag and push** — the tag must be `v` + the exact version:

   ```bash
   git checkout main && git pull
   git tag -a v0.2.0 -m "v0.2.0"
   git push origin v0.2.0
   ```

8. **Watch the runs** under *Actions*. Two workflows fire on the tag, independently:
   - **Publish to PyPI**:
     1. checks the tag equals `v` + `__version__` and that `CHANGELOG.md` has that section,
     2. runs the test suite,
     3. builds the sdist and wheel and runs `twine check --strict`,
     4. publishes to PyPI (trusted publishing),
     5. creates the GitHub Release with the changelog section as notes and the built files attached.
   - **Publish Docker image**: builds the image from this tag's source (`Dockerfile`, not the
     PyPI package) for `linux/amd64` and `linux/arm64`, and pushes
     `ghcr.io/himanshu231204/jev_model_routers:0.2.0` (plus `:latest` for a non-pre-release).

9. **Verify** in a clean environment:

   ```bash
   python -m venv /tmp/jev-check && /tmp/jev-check/bin/pip install jev-model-router==0.2.0
   /tmp/jev-check/bin/jev-claude -p "say hi"

   # or, the Docker image (entrypoint is already jev-claude):
   docker run --rm ghcr.io/himanshu231204/jev_model_routers:0.2.0 --version
   ```

## If something goes wrong

- **Tag doesn't match the version / no changelog section** — nothing was published. Delete the
  tag, fix, and tag again:

  ```bash
  git push --delete origin v0.2.0 && git tag -d v0.2.0
  ```

- **Tests or build failed** — nothing was published. Fix on `main`, then re-tag as above.

- **PyPI rejected the upload** (e.g. trusted publisher misconfigured) — check that the PyPI
  publisher's owner, repository and workflow name match exactly, then re-run the failed job.

- **A broken release reached PyPI** — PyPI never lets a version number be reused. *Yank* it on
  PyPI (*Manage → Releases → Yank*) so new installs skip it, then release a fixed patch version
  (e.g. `0.2.1`).
