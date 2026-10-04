"""A persistent headless browser driven over the DevTools protocol (stdlib only).

browser.py launches one browser per screenshot. Video needs one page that is seeked frame by
frame, so this module keeps the browser running and talks to it over a WebSocket:

    with cdp.Browser.launch(chrome, (1080, 1920)) as b:
        page = b.new_page()
        page.add_init_script(runtime_js)
        page.navigate(url)
        page.evaluate("window.__hf.ready()")
        png = page.screenshot()

The browser runs in its own process group with a throwaway profile (browser.scratch), and
leaving the block always stops it and every helper it started (browser.kill_group).
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import json
import os
import socket
import struct
import time
from collections import deque
from pathlib import Path
from typing import Any

from . import browser
from .fsutil import OperationalError

CALL_TIMEOUT_S = 30  # one protocol call; a page that stops answering is an operational failure
LAUNCH_TIMEOUT_S = 20  # until DevToolsActivePort appears
_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
# Animations run on the main thread only. With compositor-thread animations a seeked transform was
# sometimes captured from a differently rasterised layer (glyph edges differed in 7 of 40 fresh
# renders in the M0 spike; 0 of 80 with these flags).
SEEK_FLAGS = ["--disable-threaded-animation", "--disable-threaded-scrolling"]


class WebSocketClosed(OperationalError):
    pass


class WebSocket:
    """Minimal RFC 6455 client: text frames, masking, fragmentation, ping/pong, close."""

    def __init__(self, host: str, port: int, path: str, timeout: float = CALL_TIMEOUT_S) -> None:
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._buf = bytearray()
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\n"
                           f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                           "Sec-WebSocket-Version: 13\r\n\r\n").encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise WebSocketClosed("DevTools closed the connection during the handshake")
            head += chunk
        head, rest = head.split(b"\r\n\r\n", 1)
        lines = head.decode("latin-1").split("\r\n")
        if " 101 " not in lines[0] + " ":
            raise OperationalError(f"DevTools refused the WebSocket upgrade: {lines[0]}")
        headers = {k.strip().lower(): v.strip() for k, _, v in (ln.partition(":") for ln in lines[1:])}
        want = base64.b64encode(hashlib.sha1((key + _WS_GUID).encode()).digest()).decode()
        if headers.get("sec-websocket-accept") != want:
            raise OperationalError("DevTools sent a bad Sec-WebSocket-Accept")
        self._buf += rest

    def _exact(self, n: int) -> bytes:
        while len(self._buf) < n:
            chunk = self.sock.recv(max(65536, n - len(self._buf)))
            if not chunk:
                raise WebSocketClosed("the DevTools connection closed")
            self._buf += chunk
        out = bytes(self._buf[:n])
        del self._buf[:n]
        return out

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        n = len(payload)
        head = bytes([0x80 | opcode])
        if n < 126:
            head += bytes([0x80 | n])
        elif n < 65536:
            head += bytes([0x80 | 126]) + struct.pack("!H", n)
        else:
            head += bytes([0x80 | 127]) + struct.pack("!Q", n)
        mask = os.urandom(4)
        # XOR through int arithmetic: fast enough for protocol messages without numpy
        m = int.from_bytes((mask * (n // 4 + 1))[:n], "big") if n else 0
        body = (int.from_bytes(payload, "big") ^ m).to_bytes(n, "big") if n else b""
        self.sock.sendall(head + mask + body)

    def send_text(self, text: str) -> None:
        self._send_frame(0x1, text.encode("utf-8"))

    def recv_text(self, timeout: float) -> str:
        """The next complete text message; answers pings on the way."""
        self.sock.settimeout(timeout)
        parts: list[bytes] = []
        while True:
            b0, b1 = self._exact(2)
            fin, opcode, n = b0 & 0x80, b0 & 0x0F, b1 & 0x7F
            if n == 126:
                n = struct.unpack("!H", self._exact(2))[0]
            elif n == 127:
                n = struct.unpack("!Q", self._exact(8))[0]
            if b1 & 0x80:  # servers must not mask, but unmask if one does
                mask = self._exact(4)
                raw = self._exact(n)
                payload = bytes(c ^ mask[i % 4] for i, c in enumerate(raw))
            else:
                payload = self._exact(n)
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            if opcode == 0x8:
                raise WebSocketClosed("DevTools closed the connection")
            parts.append(payload)
            if fin:
                return b"".join(parts).decode("utf-8")

    def close(self) -> None:
        with contextlib.suppress(OSError):
            self._send_frame(0x8, struct.pack("!H", 1000))
        with contextlib.suppress(OSError):
            self.sock.close()


class Connection:
    """Request/response over one WebSocket; events are queued for whoever waits for them."""

    def __init__(self, ws: WebSocket) -> None:
        self.ws = ws
        self._next = 0
        self.events: deque[dict] = deque(maxlen=10000)
        self.handlers: list = []  # f(message) -> True when handled (not queued)

    def _dispatch(self, msg: dict) -> None:
        for h in self.handlers:
            if h(msg):
                return
        self.events.append(msg)

    def send(self, method: str, params: dict | None = None, session: str | None = None,
             timeout: float = CALL_TIMEOUT_S) -> dict:
        self._next += 1
        mid = self._next
        msg: dict[str, Any] = {"id": mid, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        self.ws.send_text(json.dumps(msg))
        deadline = time.monotonic() + timeout
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                raise OperationalError(f"DevTools {method} did not answer within {timeout:g} s")
            try:
                reply = json.loads(self.ws.recv_text(left))
            except socket.timeout:
                raise OperationalError(f"DevTools {method} did not answer within {timeout:g} s") from None
            if reply.get("id") == mid:
                if "error" in reply:
                    raise OperationalError(f"DevTools {method}: {reply['error'].get('message')}")
                return reply.get("result", {})
            if "method" in reply:
                self._dispatch(reply)

    def notify(self, method: str, params: dict, session: str | None = None) -> None:
        """Send without waiting for the answer (used from event handlers)."""
        self._next += 1
        msg: dict[str, Any] = {"id": self._next, "method": method, "params": params}
        if session:
            msg["sessionId"] = session
        self.ws.send_text(json.dumps(msg))

    def wait_event(self, method: str, session: str | None, timeout: float) -> dict:
        deadline = time.monotonic() + timeout
        while True:
            for ev in list(self.events):
                if ev.get("method") == method and ev.get("sessionId") == session:
                    self.events.remove(ev)
                    return ev.get("params", {})
            left = deadline - time.monotonic()
            if left <= 0:
                raise OperationalError(f"no {method} within {timeout:g} s")
            try:
                msg = json.loads(self.ws.recv_text(left))
            except socket.timeout:
                raise OperationalError(f"no {method} within {timeout:g} s") from None
            if "method" in msg:
                self._dispatch(msg)


class Page:
    def __init__(self, conn: Connection, session: str, target: str) -> None:
        self.conn, self.session, self.target = conn, session, target
        self.errors: list[str] = []
        self._blocked: list[str] = []
        conn.handlers.append(self._on_event)

    def _on_event(self, msg: dict) -> bool:
        if msg.get("sessionId") != self.session:
            return False
        m, p = msg.get("method"), msg.get("params", {})
        if m == "Fetch.requestPaused":
            url = p["request"]["url"]
            if url.split(":", 1)[0].lower() in ("file", "data", "blob", "about"):
                self.conn.notify("Fetch.continueRequest", {"requestId": p["requestId"]}, self.session)
            else:
                self._blocked.append(url)
                self.conn.notify("Fetch.failRequest", {"requestId": p["requestId"], "errorReason": "BlockedByClient"},
                                 self.session)
            return True
        if m == "Runtime.exceptionThrown":
            d = p.get("exceptionDetails", {})
            self.errors.append((d.get("exception") or {}).get("description") or d.get("text", "exception"))
            return True
        if m == "Runtime.consoleAPICalled" and p.get("type") in ("error", "assert"):
            self.errors.append(" ".join(str(a.get("value", a.get("description", ""))) for a in p.get("args", [])))
            return True
        return m in ("Runtime.consoleAPICalled", "Runtime.executionContextCreated",
                     "Runtime.executionContextsCleared", "Runtime.executionContextDestroyed")

    def send(self, method: str, params: dict | None = None, timeout: float = CALL_TIMEOUT_S) -> dict:
        return self.conn.send(method, params, self.session, timeout)

    @property
    def blocked(self) -> list[str]:
        """URLs refused by block_network(), in request order."""
        return list(self._blocked)

    def set_viewport(self, size: tuple[int, int]) -> None:
        self.send("Emulation.setDeviceMetricsOverride",
                  {"width": size[0], "height": size[1], "deviceScaleFactor": 1, "mobile": False})

    def transparent(self) -> None:
        self.send("Emulation.setDefaultBackgroundColorOverride", {"color": {"r": 0, "g": 0, "b": 0, "a": 0}})

    def block_network(self) -> None:
        """Refuse every request that is not file:, data:, blob: or about: (no network at render time)."""
        self.send("Fetch.enable", {"patterns": [{"urlPattern": "*"}]})

    def add_init_script(self, source: str) -> None:
        """Runs before any page script in every document this page loads."""
        self.send("Page.addScriptToEvaluateOnNewDocument", {"source": source})

    def navigate(self, url: str, timeout: float = CALL_TIMEOUT_S) -> None:
        res = self.send("Page.navigate", {"url": url}, timeout)
        if res.get("errorText"):
            raise OperationalError(f"could not open {url}: {res['errorText']}")
        self.conn.wait_event("Page.loadEventFired", self.session, timeout)

    def evaluate(self, expression: str, timeout: float = CALL_TIMEOUT_S) -> Any:
        """Evaluate in the page, awaiting a returned promise; returns the JSON value."""
        res = self.send("Runtime.evaluate", {"expression": expression, "awaitPromise": True,
                                             "returnByValue": True}, timeout)
        if "exceptionDetails" in res:
            d = res["exceptionDetails"]
            text = (d.get("exception") or {}).get("description") or d.get("text", "exception")
            raise OperationalError(f"page script failed: {text.splitlines()[0][:300]}")
        return res.get("result", {}).get("value")

    def screenshot(self, fmt: str = "png", quality: int | None = None) -> bytes:
        params: dict[str, Any] = {"format": fmt, "fromSurface": True}
        if fmt == "jpeg" and quality is not None:
            params["quality"] = quality
        return base64.b64decode(self.send("Page.captureScreenshot", params)["data"])


class Browser:
    def __init__(self) -> None:
        self._stack = contextlib.ExitStack()
        self.proc = None
        self.conn: Connection | None = None

    @classmethod
    def launch(cls, chrome: str, size: tuple[int, int], transparent: bool = False,
               extra_args: list[str] | None = None) -> "Browser":
        b = cls()
        try:
            tmp = b._stack.enter_context(browser.scratch())
            profile = tmp / "profile"
            argv = browser.cmd(chrome, str(profile), size, budget_ms=None, transparent=transparent)
            argv += [*SEEK_FLAGS, *(extra_args or []), "--remote-debugging-port=0", "--remote-allow-origins=*", "about:blank"]
            b.proc = browser.spawn(argv, tmp / "stdout", tmp / "stderr")
            b._stack.callback(b._stop)
            port, path = b._active_port(profile, tmp / "stderr")
            b.conn = Connection(WebSocket("127.0.0.1", port, path))
            b._stack.callback(b._bye)
        except BaseException:
            b._stack.close()
            raise
        return b

    def _active_port(self, profile: Path, err: Path) -> tuple[int, str]:
        f = profile / "DevToolsActivePort"
        deadline = time.monotonic() + LAUNCH_TIMEOUT_S
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                tail = err.read_bytes().decode(errors="replace")[-300:] if err.is_file() else ""
                raise OperationalError(f"the browser exited ({self.proc.returncode}) before DevTools started: {tail}")
            with contextlib.suppress(OSError, ValueError):
                lines = f.read_text().split()
                if len(lines) >= 2:
                    return int(lines[0]), lines[1]
            time.sleep(0.05)
        raise OperationalError(f"DevTools did not start within {LAUNCH_TIMEOUT_S} s "
                               "(a RemoteDebuggingAllowed=false policy blocks it)")

    def _bye(self) -> None:
        with contextlib.suppress(Exception):
            self.conn.notify("Browser.close", {})
        self.conn.ws.close()

    def _stop(self) -> None:
        if self.proc is not None:
            try:
                self.proc.wait(timeout=browser.GRACE_S)
            except Exception:
                pass
            browser.kill_group(self.proc)
            with contextlib.suppress(Exception):
                self.proc.kill()
                self.proc.wait(timeout=10)

    def new_page(self, size: tuple[int, int] | None = None) -> Page:
        assert self.conn is not None
        target = self.conn.send("Target.createTarget", {"url": "about:blank"})["targetId"]
        session = self.conn.send("Target.attachToTarget", {"targetId": target, "flatten": True})["sessionId"]
        page = Page(self.conn, session, target)
        page.send("Page.enable")
        page.send("Runtime.enable")
        if size:
            page.set_viewport(size)
        return page

    def close(self) -> None:
        self._stack.close()

    def __enter__(self) -> "Browser":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
