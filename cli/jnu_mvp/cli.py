"""jnu-mvp CLI.

  mvp login              API 토큰 저장 (마이페이지에서 발급)
  mvp link <MVP_ID>      현재 디렉터리를 MVP에 연결 (jnu-mvp.json 생성)
  mvp push [path]        zip 생성 → 업로드 (--publish로 게시 신청까지)
  mvp publish [--version N]
  mvp status             버전 이력 조회
"""

import argparse
import getpass
import json
import sys
from pathlib import Path

import requests

from jnu_mvp.pack import make_zip

CONFIG_PATH = Path.home() / ".jnu-mvp" / "config.json"
PROJECT_FILE = "jnu-mvp.json"
DEFAULT_API_BASE = "http://localhost:8000"


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def _save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


def _auth_headers() -> dict:
    config = _load_config()
    token = config.get("token")
    if not token:
        sys.exit("로그인이 필요합니다: mvp login")
    return {"Authorization": f"Bearer {token}"}


def _api_base() -> str:
    return _load_config().get("api_base", DEFAULT_API_BASE)


def _project_mvp_id(path: Path) -> int:
    project_file = path / PROJECT_FILE
    if not project_file.exists():
        sys.exit(f"{PROJECT_FILE}이 없습니다. 먼저 실행하세요: mvp link <MVP_ID>")
    return int(json.loads(project_file.read_text(encoding="utf-8"))["mvp_id"])


def cmd_login(args) -> None:
    api_base = args.api_base or _load_config().get("api_base", DEFAULT_API_BASE)
    token = args.token or getpass.getpass("API 토큰 (jnu_...): ")
    r = requests.get(f"{api_base}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        sys.exit("토큰 검증 실패. 마이페이지에서 발급한 API 토큰인지 확인해주세요.")
    me = r.json()
    if not me["jnu_verified"]:
        sys.exit("전남대 이메일 인증이 완료되지 않은 계정입니다.")
    _save_config({"api_base": api_base, "token": token})
    print(f"로그인 완료: {me['nickname']} ({me['email']})")


def cmd_link(args) -> None:
    Path(PROJECT_FILE).write_text(
        json.dumps({"mvp_id": args.mvp_id}, indent=2), encoding="utf-8"
    )
    print(f"연결 완료: MVP #{args.mvp_id} → ./{PROJECT_FILE}")


def cmd_push(args) -> None:
    root = Path(args.path)
    mvp_id = args.mvp_id or _project_mvp_id(root)
    print(f"패킹 중: {root.resolve()}")
    data = make_zip(root)
    print(f"업로드 중: MVP #{mvp_id} ({len(data) / 1024:.1f} KB)")
    r = requests.post(
        f"{_api_base()}/api/mvps/{mvp_id}/artifacts",
        headers=_auth_headers(),
        files={"file": ("site.zip", data, "application/zip")},
        data={"channel": "cli"},
    )
    if r.status_code != 201:
        sys.exit(f"업로드 실패 ({r.status_code}): {r.json().get('detail', r.text)}")
    version = r.json()["version"]
    print(f"업로드 완료: v{version} (draft)")

    if args.publish:
        _publish(mvp_id, version)
    else:
        print(f"게시하려면: mvp publish --version {version}")


def _publish(mvp_id: int, version: int) -> None:
    r = requests.post(
        f"{_api_base()}/api/mvps/{mvp_id}/artifacts/{version}/publish",
        headers=_auth_headers(),
    )
    if r.status_code != 200:
        sys.exit(f"게시 신청 실패 ({r.status_code}): {r.json().get('detail', r.text)}")
    print(f"게시 신청 완료: v{version} → 본부 관리자 승인 후 공개됩니다 (status={r.json()['mvp_status']})")


def cmd_publish(args) -> None:
    mvp_id = args.mvp_id or _project_mvp_id(Path("."))
    version = args.version
    if version is None:
        r = requests.get(f"{_api_base()}/api/mvps/{mvp_id}/artifacts", headers=_auth_headers())
        if r.status_code != 200 or not r.json():
            sys.exit("업로드된 버전이 없습니다. 먼저 실행하세요: mvp push")
        version = r.json()[0]["version"]
    _publish(mvp_id, version)


def cmd_status(args) -> None:
    mvp_id = args.mvp_id or _project_mvp_id(Path("."))
    r = requests.get(f"{_api_base()}/api/mvps/{mvp_id}/artifacts", headers=_auth_headers())
    if r.status_code != 200:
        sys.exit(f"조회 실패 ({r.status_code}): {r.json().get('detail', r.text)}")
    print(f"MVP #{mvp_id} 버전 이력:")
    for a in r.json():
        print(f"  v{a['version']:<3} {a['publish_status']:<10} {a['upload_channel']:<4} "
              f"{a['file_size'] / 1024:.1f} KB  {a['uploaded_at']}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="mvp", description="전남대 MVP 플랫폼 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("login", help="API 토큰으로 로그인")
    p.add_argument("--token", help="API 토큰 (미지정 시 입력 프롬프트)")
    p.add_argument("--api-base", help=f"API 주소 (기본 {DEFAULT_API_BASE})")
    p.set_defaults(func=cmd_login)

    p = sub.add_parser("link", help="현재 디렉터리를 MVP에 연결")
    p.add_argument("mvp_id", type=int)
    p.set_defaults(func=cmd_link)

    p = sub.add_parser("push", help="zip 생성 후 업로드")
    p.add_argument("path", nargs="?", default=".")
    p.add_argument("--mvp-id", type=int)
    p.add_argument("--publish", action="store_true", help="업로드 후 게시 신청까지")
    p.set_defaults(func=cmd_push)

    p = sub.add_parser("publish", help="업로드된 버전 게시 신청")
    p.add_argument("--mvp-id", type=int)
    p.add_argument("--version", type=int)
    p.set_defaults(func=cmd_publish)

    p = sub.add_parser("status", help="버전 이력 조회")
    p.add_argument("--mvp-id", type=int)
    p.set_defaults(func=cmd_status)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
