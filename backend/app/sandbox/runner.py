"""정적 웹 MVP 샌드박스 러너 (1차).

zip → nginx 이미지 빌드 → 컨테이너 실행 → Traefik /run/{slug} 라우팅.
컨테이너 제약: CPU/메모리 제한, 아웃바운드 차단(내부 네트워크), 비루트(nginx) 실행.
"""

import io
import logging
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Protocol

from app.config import get_settings

logger = logging.getLogger("jnu.sandbox")

NGINX_CONF = """\
server {
    listen 8080;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;
    location ~ \\.map$ { return 404; }
    location / { try_files $uri $uri/ /index.html; }
}
"""

DOCKERFILE = """\
FROM nginx:1.27-alpine
RUN chown -R nginx:nginx /var/cache/nginx /var/log/nginx /etc/nginx/conf.d \\
    && touch /var/run/nginx.pid && chown nginx:nginx /var/run/nginx.pid
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY site/ /usr/share/nginx/html/
USER nginx
EXPOSE 8080
"""


def route_slug(mvp_id: int) -> str:
    return f"mvp-{mvp_id}"


class SandboxRunner(Protocol):
    def start(self, mvp_id: int, zip_data: bytes) -> str:
        """컨테이너를 기동하고 container_id를 반환."""
        ...

    def stop(self, container_id: str) -> None: ...


class DockerSandboxRunner:
    """Docker Engine API 기반 러너. Docker 데몬이 필요하다."""

    def __init__(self):
        import docker

        self.client = docker.from_env()
        self.settings = get_settings()

    def start(self, mvp_id: int, zip_data: bytes) -> str:
        slug = route_slug(mvp_id)
        image_tag = f"jnu-mvp/{slug}:latest"

        build_dir = Path(tempfile.mkdtemp(prefix=f"jnu-{slug}-"))
        try:
            site_dir = build_dir / "site"
            site_dir.mkdir()
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                zf.extractall(site_dir)  # 업로드 시 zip slip 검증 완료된 데이터
            (build_dir / "nginx.conf").write_text(NGINX_CONF)
            (build_dir / "Dockerfile").write_text(DOCKERFILE)
            self.client.images.build(path=str(build_dir), tag=image_tag, rm=True)
        finally:
            shutil.rmtree(build_dir, ignore_errors=True)

        # 기존 컨테이너 정리 후 재기동
        for c in self.client.containers.list(all=True, filters={"name": slug}):
            c.remove(force=True)

        container = self.client.containers.run(
            image_tag,
            name=slug,
            detach=True,
            network=self.settings.sandbox_network,
            mem_limit=self.settings.sandbox_mem_limit,
            nano_cpus=int(self.settings.sandbox_cpu_quota * 1e9),
            read_only=True,
            # 비루트(nginx) 실행이므로 tmpfs는 쓰기 가능 모드로 마운트
            tmpfs={
                "/var/cache/nginx": "mode=1777",
                "/var/run": "mode=1777",
                "/tmp": "mode=1777",
            },
            labels={
                "traefik.enable": "true",
                "jnu.sandbox": "true",
                f"traefik.http.routers.{slug}.rule": f"PathPrefix(`/run/{slug}`)",
                f"traefik.http.routers.{slug}.middlewares": f"{slug}-strip",
                f"traefik.http.middlewares.{slug}-strip.stripprefix.prefixes": f"/run/{slug}",
                f"traefik.http.services.{slug}.loadbalancer.server.port": "8080",
            },
        )
        logger.info("샌드박스 기동: %s (%s)", slug, container.short_id)
        return container.id

    def stop(self, container_id: str) -> None:
        try:
            c = self.client.containers.get(container_id)
            c.remove(force=True)
        except Exception:
            logger.warning("컨테이너 정리 실패(이미 없음일 수 있음): %s", container_id)


_runner: SandboxRunner | None = None


def get_runner() -> SandboxRunner:
    global _runner
    if _runner is None:
        _runner = DockerSandboxRunner()
    return _runner


def set_runner_for_testing(runner: SandboxRunner) -> None:
    global _runner
    _runner = runner
