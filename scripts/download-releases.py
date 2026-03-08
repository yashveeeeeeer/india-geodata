#!/usr/bin/env python3
"""Download all GitHub Release assets for the india-geodata repository.

Fetches every release from the GitHub API and downloads all attached assets
into subdirectories organized by release tag. Supports authentication,
retry logic with exponential backoff, rate-limit handling, and resumption
of partially completed downloads.

Usage:
    GITHUB_TOKEN=xxx python scripts/download-releases.py [OPTIONS]

Options:
    --repo OWNER/REPO   GitHub repository (default: auto-detected from git remote)
    --dir PATH          Download directory (default: ./downloads)
    --token TOKEN       GitHub personal access token (overrides GITHUB_TOKEN env var)

Environment Variables:
    GITHUB_TOKEN        GitHub personal access token for API authentication
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request


# Constants
GITHUB_API_BASE = "https://api.github.com"
MAX_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 1.0
BACKOFF_MULTIPLIER = 2.0
CHUNK_SIZE = 8192


def detect_repo_from_git():
    """Detect the GitHub repository from the git remote origin URL.

    Returns:
        A string like 'OWNER/REPO', or None if detection fails.
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return None

    # Match HTTPS: https://github.com/OWNER/REPO.git
    match = re.search(r"github\.com[/:]([^/]+)/([^/.]+?)(?:\.git)?$", url)
    if match:
        return f"{match.group(1)}/{match.group(2)}"

    return None


def make_request(url, token=None, accept=None, stream=False):
    """Make an HTTP request to the GitHub API or asset URL.

    Args:
        url: The URL to request.
        token: Optional GitHub token for authentication.
        accept: Optional Accept header value.
        stream: If True, return the response object without reading it.

    Returns:
        If stream is False, returns a tuple of (response_body_bytes, headers).
        If stream is True, returns the response object (caller must close it).

    Raises:
        urllib.error.HTTPError: On HTTP errors.
        urllib.error.URLError: On network errors.
    """
    headers = {"User-Agent": "india-geodata-downloader/1.0"}
    if token:
        headers["Authorization"] = f"token {token}"
    if accept:
        headers["Accept"] = accept
    else:
        headers["Accept"] = "application/vnd.github.v3+json"

    req = urllib.request.Request(url, headers=headers)

    response = urllib.request.urlopen(req, timeout=60)
    if stream:
        return response

    body = response.read()
    return body, response.headers


def check_rate_limit(headers):
    """Check GitHub API rate limit headers and sleep if necessary.

    Args:
        headers: HTTP response headers.
    """
    remaining = headers.get("X-RateLimit-Remaining")
    reset_time = headers.get("X-RateLimit-Reset")

    if remaining is not None and int(remaining) <= 1:
        if reset_time is not None:
            reset_ts = int(reset_time)
            now = int(time.time())
            wait = max(reset_ts - now + 1, 1)
            print(f"  Rate limit nearly exhausted. Waiting {wait}s for reset...")
            time.sleep(wait)


def fetch_all_releases(repo, token=None):
    """Fetch all releases from the GitHub API, handling pagination.

    Args:
        repo: GitHub repository in 'OWNER/REPO' format.
        token: Optional GitHub personal access token.

    Returns:
        A list of release dicts from the GitHub API.
    """
    releases = []
    page = 1
    per_page = 30

    while True:
        url = f"{GITHUB_API_BASE}/repos/{repo}/releases?per_page={per_page}&page={page}"
        print(f"  Fetching releases page {page}...")

        body, headers = make_request(url, token=token)
        check_rate_limit(headers)

        page_releases = json.loads(body.decode("utf-8"))
        if not page_releases:
            break

        releases.extend(page_releases)
        page += 1

        # Check if there's a next page via Link header
        link_header = headers.get("Link", "")
        if 'rel="next"' not in link_header:
            break

    return releases


def download_asset(asset_url, dest_path, expected_size, token=None):
    """Download a single release asset with retry logic.

    Args:
        asset_url: The GitHub API URL for the asset.
        dest_path: Local file path to save the asset to.
        expected_size: Expected file size in bytes for verification.
        token: Optional GitHub personal access token.

    Returns:
        True if the download succeeded, False otherwise.
    """
    backoff = INITIAL_BACKOFF_SECONDS

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = make_request(
                asset_url,
                token=token,
                accept="application/octet-stream",
                stream=True,
            )

            # Write to a temporary file first, then rename
            tmp_path = dest_path + ".tmp"
            downloaded = 0

            try:
                with open(tmp_path, "wb") as f:
                    while True:
                        chunk = response.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
            finally:
                response.close()

            # Verify size if known
            if expected_size and downloaded != expected_size:
                print(
                    f"    Size mismatch: expected {expected_size}, got {downloaded}. "
                    f"Retrying ({attempt}/{MAX_RETRIES})..."
                )
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                time.sleep(backoff)
                backoff *= BACKOFF_MULTIPLIER
                continue

            # Success: rename temp file to final destination
            if os.path.exists(dest_path):
                os.remove(dest_path)
            os.rename(tmp_path, dest_path)
            return True

        except urllib.error.HTTPError as e:
            if e.code == 403:
                # Possible rate limit
                retry_after = e.headers.get("Retry-After")
                reset_time = e.headers.get("X-RateLimit-Reset")
                if retry_after:
                    wait = int(retry_after)
                elif reset_time:
                    wait = max(int(reset_time) - int(time.time()) + 1, 1)
                else:
                    wait = backoff
                print(f"    Rate limited (403). Waiting {wait}s... ({attempt}/{MAX_RETRIES})")
                time.sleep(wait)
                backoff *= BACKOFF_MULTIPLIER
                continue
            else:
                print(f"    HTTP {e.code}: {e.reason} ({attempt}/{MAX_RETRIES})")
                time.sleep(backoff)
                backoff *= BACKOFF_MULTIPLIER
                continue

        except (urllib.error.URLError, OSError) as e:
            print(f"    Network error: {e} ({attempt}/{MAX_RETRIES})")
            time.sleep(backoff)
            backoff *= BACKOFF_MULTIPLIER
            continue

    # Clean up temp file if all retries failed
    tmp_path = dest_path + ".tmp"
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    return False


def should_skip_asset(dest_path, expected_size):
    """Check if an asset has already been downloaded with matching size.

    Args:
        dest_path: Local file path where the asset would be saved.
        expected_size: Expected file size in bytes.

    Returns:
        True if the file exists and matches the expected size.
    """
    if not os.path.exists(dest_path):
        return False
    if expected_size is None or expected_size == 0:
        return False
    actual_size = os.path.getsize(dest_path)
    return actual_size == expected_size


def main():
    """Main entry point for release asset downloading."""
    parser = argparse.ArgumentParser(
        description="Download all GitHub Release assets for the india-geodata repository."
    )
    parser.add_argument(
        "--repo",
        default=None,
        help="GitHub repository in OWNER/REPO format (default: auto-detect from git remote)",
    )
    parser.add_argument(
        "--dir",
        default="./downloads",
        help="Download directory (default: ./downloads)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="GitHub personal access token (overrides GITHUB_TOKEN env var)",
    )
    args = parser.parse_args()

    # Resolve token
    token = args.token or os.environ.get("GITHUB_TOKEN")
    if not token:
        print(
            "WARNING: No GitHub token provided. API rate limits will be very low.\n"
            "  Set GITHUB_TOKEN env var or use --token argument.",
            file=sys.stderr,
        )

    # Resolve repository
    repo = args.repo
    if not repo:
        repo = detect_repo_from_git()
        if not repo:
            print(
                "ERROR: Could not detect repository from git remote.\n"
                "  Use --repo OWNER/REPO to specify it explicitly.",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"Detected repository: {repo}")
    else:
        print(f"Repository: {repo}")

    # Validate repo format
    if "/" not in repo or repo.count("/") != 1:
        print(f"ERROR: Invalid repo format '{repo}'. Expected OWNER/REPO.", file=sys.stderr)
        sys.exit(1)

    download_dir = os.path.abspath(args.dir)
    os.makedirs(download_dir, exist_ok=True)
    print(f"Download directory: {download_dir}")
    print()

    # Fetch releases
    print("Fetching releases...")
    try:
        releases = fetch_all_releases(repo, token=token)
    except urllib.error.HTTPError as e:
        print(f"ERROR: Failed to fetch releases: HTTP {e.code} {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: Failed to fetch releases: {e.reason}", file=sys.stderr)
        sys.exit(1)

    if not releases:
        print("No releases found.")
        sys.exit(0)

    print(f"Found {len(releases)} release(s).")
    print()

    # Process each release
    total_assets = 0
    downloaded_count = 0
    skipped_count = 0
    failed_count = 0

    for release in releases:
        tag = release.get("tag_name", "unknown")
        assets = release.get("assets", [])

        if not assets:
            print(f"[{tag}] No assets, skipping.")
            continue

        print(f"[{tag}] {len(assets)} asset(s)")
        tag_dir = os.path.join(download_dir, tag)
        os.makedirs(tag_dir, exist_ok=True)

        for asset in assets:
            asset_name = asset.get("name", "unknown")
            asset_url = asset.get("url", "")
            asset_size = asset.get("size", 0)
            dest_path = os.path.join(tag_dir, asset_name)
            total_assets += 1

            # Skip if already downloaded with correct size
            if should_skip_asset(dest_path, asset_size):
                size_mb = asset_size / (1024 * 1024)
                print(f"  SKIP  {asset_name} ({size_mb:.1f} MB, already exists)")
                skipped_count += 1
                continue

            size_mb = asset_size / (1024 * 1024) if asset_size else 0
            print(f"  DOWN  {asset_name} ({size_mb:.1f} MB)...", end=" ", flush=True)

            success = download_asset(asset_url, dest_path, asset_size, token=token)
            if success:
                print("OK")
                downloaded_count += 1
            else:
                print("FAILED")
                failed_count += 1

    # Print summary
    print()
    print("=" * 60)
    print(f"Summary:")
    print(f"  Releases:    {len(releases)}")
    print(f"  Total assets: {total_assets}")
    print(f"  Downloaded:  {downloaded_count}")
    print(f"  Skipped:     {skipped_count}")
    print(f"  Failed:      {failed_count}")
    print("=" * 60)

    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
