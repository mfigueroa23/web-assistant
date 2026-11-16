import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
RELEASE = (WORKFLOWS / "release.yaml").read_text()
SECURITY = (WORKFLOWS / "security.yaml").read_text()
TESTING = (WORKFLOWS / "testing.yaml").read_text()


def job(workflow: str, name: str) -> str:
    match = re.search(rf"^  {name}:\n(.*?)(?=^  [a-z-]+:\n|\Z)", workflow, flags = re.MULTILINE | re.DOTALL)
    assert match, f"missing job {name}"
    return match.group(1)


def test_testing_runs_pyright_and_pytest_on_prs_to_main():
    assert re.search(r"pull_request:\n\s+branches:\n\s+- main", TESTING)
    assert "uv run pyright" in TESTING and "uv run pytest" in TESTING


def test_security_runs_every_scanner():
    for name in ("codeql", "sonar", "osv", "dependency-review", "image"):
        job(SECURITY, name)
    assert "workflow_call:" in SECURITY


def test_release_builds_each_platform_on_its_native_runner_without_qemu():
    package = job(RELEASE, "package")
    assert "setup-qemu-action" not in RELEASE
    assert re.search(r"- arch: amd64\n\s+runner: ubuntu-24\.04\n", package)
    assert re.search(r"- arch: arm64\n\s+runner: ubuntu-24\.04-arm\n", package)
    assert "runs-on: ${{ matrix.runner }}" in package
    assert "platforms: linux/${{ matrix.arch }}" in package


def test_release_publishes_only_the_commit_tag_before_the_scan():
    package, merge = job(RELEASE, "package"), job(RELEASE, "merge")
    assert "push-by-digest=true" in package and "tags:" not in package
    assert "needs: package" in merge
    assert '--tag "$REPOSITORY:sha-$GITHUB_SHA"' in merge


def test_release_tags_version_and_latest_only_after_the_scan():
    promote = job(RELEASE, "promote")
    assert "- scan" in promote
    assert '"$published" != "$DIGEST"' in promote
    assert '--tag "$REPOSITORY:$VERSION"' in promote and '--tag "$REPOSITORY:latest"' in promote


def test_release_migrates_before_deploying_the_scanned_digest():
    migrate, deploy = job(RELEASE, "migrate"), job(RELEASE, "deploy")
    assert "needs: promote" in migrate and "uv run --no-sync alembic upgrade head" in migrate
    assert "- migrate" in deploy
    assert "${{ needs.merge.outputs.digest }}" in deploy
    assert 'set image deployment/web web="$IMAGE" -n virtual-assistant' in deploy
    assert "rollout status deployment/web -n virtual-assistant" in deploy


def test_docker_scout_applies_the_vex_statements():
    image = job(SECURITY, "image")
    assert image.count("vex-location: .github/vex") == 2
    assert image.count("vex-author: mfigueroa23") == 2


def test_every_vex_statement_justifies_why_the_image_is_not_affected():
    statements = [json.loads(path.read_text()) for path in (ROOT / ".github" / "vex").glob("*.json")]
    assert statements
    for document in statements:
        assert document["@context"] == "https://openvex.dev/ns/v0.2.0"
        for statement in document["statements"]:
            assert statement["status"] == "not_affected"
            assert statement["justification"] and statement["impact_statement"]


def test_vex_statements_accept_the_unfixed_openssl_cves():
    # Remove this test with the statements once Alpine 3.24 ships openssl 3.5.9-r1.
    product = "pkg:apk/alpine/openssl@3.5.9-r0?os_name=alpine&os_version=3.24"
    for cve in ("CVE-2026-107496", "CVE-2026-88822", "CVE-2026-88823", "CVE-2026-95691", "CVE-2026-95692"):
        document = json.loads((ROOT / ".github" / "vex" / f"{cve}.json").read_text())
        assert document["@id"].endswith(f"/.github/vex/{cve}.json")
        [statement] = document["statements"]
        assert statement["vulnerability"]["name"] == cve
        assert statement["products"] == [{"@id": product}]
        assert statement["justification"] == "vulnerable_code_not_in_execute_path"
        assert "openssl 3.5.9-r1" in statement["impact_statement"]
