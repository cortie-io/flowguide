"""사용자가 보낸 n8n 주소 검사 — 서버가 대신 요청을 보내므로 내부망(beta 자신·사설 IP·메타데이터)으로 향하지 못하게 한다(SSRF 방지).

공인 IP로만 풀리는 http(s) 주소만 통과한다. 빈 값(None·"")은 그대로 둔다(연결 안 함).
"""
from __future__ import annotations

import ipaddress
import socket
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import AfterValidator


def check_public_url(url: str | None) -> str | None:
    if not url:
        return url
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("n8n 주소는 http(s)://로 시작해야 합니다.")
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80))
    except socket.gaierror:
        raise ValueError("n8n 주소를 찾을 수 없습니다.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if not ip.is_global:
            raise ValueError("내부 주소로는 연결할 수 없습니다. 인터넷에서 접속되는 n8n 주소를 입력하세요.")
    return url


PublicUrl = Annotated[str, AfterValidator(check_public_url)]
