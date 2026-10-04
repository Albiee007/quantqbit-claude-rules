"""Library checks for the video renderer that need no browser and no ffmpeg (tests/video.test.sh).

WebSocket client against a stdlib echo server (masking, 16/64-bit lengths, an 8 MB message,
fragmentation, ping/pong, close); whole-frame scene arithmetic; planned captions; the flashing
heuristic; output-profile checks; cubicBezier tokens; ffmpeg lookup advice. One line per check;
exit 1 when any fails.
"""

from __future__ import annotations

import base64
import hashlib
import os
import socket
import struct
import sys
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "harness" / "lib"))
sys.dont_write_bytecode = True
from harnesslib import cdp, dtcg, framecheck  # noqa: E402
from harnesslib import ffmpeg as ffm  # noqa: E402
from harnesslib import video as vd  # noqa: E402
from harnesslib.fsutil import OperationalError  # noqa: E402

failed = 0


def check(ok: bool, what: str) -> None:
    global failed
    print(("ok    " if ok else "FAIL  ") + what)
    failed += not ok


# ------------------------------------------------------------------ websocket echo server

def _frame(opcode: int, payload: bytes, fin: bool = True) -> bytes:
    n = len(payload)
    head = bytes([(0x80 if fin else 0) | opcode])
    if n < 126:
        head += bytes([n])
    elif n < 65536:
        head += bytes([126]) + struct.pack("!H", n)
    else:
        head += bytes([127]) + struct.pack("!Q", n)
    return head + payload


def _read_frame(conn: socket.socket, buf: bytearray) -> tuple[int, bytes, bool]:
    def need(k: int) -> bytes:
        while len(buf) < k:
            chunk = conn.recv(1 << 20)
            if not chunk:
                raise ConnectionError
            buf.extend(chunk)
        out = bytes(buf[:k])
        del buf[:k]
        return out
    b0, b1 = need(2)
    n = b1 & 0x7F
    if n == 126:
        n = struct.unpack("!H", need(2))[0]
    elif n == 127:
        n = struct.unpack("!Q", need(8))[0]
    masked = bool(b1 & 0x80)
    mask = need(4) if masked else b"\0\0\0\0"
    data = need(n)
    m = int.from_bytes((mask * (n // 4 + 1))[:n], "big") if n else 0
    data = (int.from_bytes(data, "big") ^ m).to_bytes(n, "big") if n else b""
    return b0 & 0x0F, data, masked


def serve(listener: socket.socket, log: list) -> None:
    conn, _ = listener.accept()
    req = b""
    while b"\r\n\r\n" not in req:
        req += conn.recv(4096)
    key = [ln.split(b":", 1)[1].strip() for ln in req.split(b"\r\n") if ln.lower().startswith(b"sec-websocket-key")][0]
    acc = base64.b64encode(hashlib.sha1(key + b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest())
    conn.sendall(b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                 b"Sec-WebSocket-Accept: " + acc + b"\r\n\r\n")
    buf = bytearray()
    while True:
        try:
            op, data, masked = _read_frame(conn, buf)
        except ConnectionError:
            break
        log.append((op, len(data), masked))
        if op == 0x1:
            text = data.decode()
            if text == "fragment":
                conn.sendall(_frame(0x1, b"frag", fin=False) + _frame(0x0, b"ment", fin=True))
            elif text == "ping":
                conn.sendall(_frame(0x9, b"hi") + _frame(0x1, b"after-ping"))
            elif text == "close":
                conn.sendall(_frame(0x8, struct.pack("!H", 1000)))
            else:
                conn.sendall(_frame(0x1, data))
        elif op == 0x8:
            break
    conn.close()


def websocket_checks() -> None:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    log: list = []
    t = threading.Thread(target=serve, args=(listener, log), daemon=True)
    t.start()
    ws = cdp.WebSocket("127.0.0.1", listener.getsockname()[1], "/devtools/browser/x", timeout=10)
    for size in (5, 200, 70_000, 8 * 1024 * 1024):
        msg = ("x" * (size - 1)) + "y"
        ws.send_text(msg)
        check(ws.recv_text(30) == msg, f"websocket echoes a {size}-byte message")
    check(all(m for op, _, m in log if op == 0x1), "every client frame is masked")
    ws.send_text("fragment")
    check(ws.recv_text(10) == "fragment", "a fragmented message is reassembled")
    ws.send_text("ping")
    check(ws.recv_text(10) == "after-ping", "a ping is answered and the next message still arrives")
    ws.send_text("sync")  # the server reads frames in order, so the pong is logged before this echo
    ws.recv_text(10)
    check(any(op == 0xA for op, _, _ in log), "the client answered the ping with a pong")
    ws.send_text("close")
    try:
        ws.recv_text(10)
        closed = False
    except cdp.WebSocketClosed:
        closed = True
    check(closed, "a close frame ends the connection with WebSocketClosed")
    ws.close()
    listener.close()


# ------------------------------------------------------------------ frame plan

AD = {"motion": {"durations": {"fast": 200, "base": 400, "slow": 640}, "easing": {}, "stagger": {"perItemMs": 50, "maxItems": 4},
                 "transitions": ["cut", "fade"], "defaultTransition": "fade", "textIn": "fade-up", "textOut": "none"},
      "pace": {"readingWpm": 200, "minHold": 1.0, "voWpm": 150}, "layouts": ["type-start"], "defaultLayout": "type-start",
      "sceneTemplates": ["title", "feature", "stat", "end-card"], "backgrounds": {"a": {}}, "defaultBackground": "a",
      "endCard": {"background": "a", "logo": False}, "subtitles": None}


def piece(scenes: list[dict], fps: int = 30) -> dict:
    return {"schemaVersion": 1, "id": "t", "kind": "social", "formats": ["social-9x16"], "fps": fps, "scenes": scenes}


def plan_checks() -> None:
    check(vd.frames_of(1.5, 30) == 45 and vd.frames_of(0.0166, 30) == 0 and vd.frames_of(1 / 60, 30) == 1,
          "seconds round to whole frames with floor(s * fps + 0.5)")
    sc = [{"id": "a", "template": "title", "duration": 3, "copy": {"head": "Hi"}},
          {"id": "b", "template": "title", "duration": 4, "copy": {"head": "There"}, "transitionIn": {"type": "fade", "duration": 0.5}},
          {"id": "c", "template": "title", "duration": 3, "copy": {"head": "End"}, "transitionIn": {"type": "cut"}}]
    pl = vd.plan(None, "t", piece(sc), AD, "social-9x16", production=False)
    starts = [(s.start, s.frames, s.overlap) for s in pl.scenes]
    check(starts == [(0, 90, 0), (75, 120, 15), (195, 90, 0)] and pl.frames == 285,
          f"overlapping transitions: starts, lengths, overlaps {starts}, total {pl.frames} (want 285)")
    check(not pl.errors, f"a well-timed piece has no errors ({pl.errors})")
    a = pl.scenes[0]
    check(a.hold_end == 90 - 15 and a.hold_start == 12 and a.hold_start <= a.probe - a.start < a.hold_end,
          f"the still part leaves room for the next transition and the probe sits inside it ({a.hold_start}-{a.hold_end}, probe {a.probe})")
    short = [{"id": "a", "template": "title", "duration": 3, "copy": {"head": "Hi"}},
             {"id": "b", "template": "title", "duration": 1, "copy": {"head": "Too quick"}}]
    pl = vd.plan(None, "t", piece(short), AD, "social-9x16", production=False)
    check(any("minimum hold" in e for e in pl.errors), "a scene shorter than the minimum hold fails")
    odd = [{"id": "a", "template": "title", "duration": 3.01, "copy": {"head": "Hi"}}]
    pl = vd.plan(None, "t", piece(odd), AD, "social-9x16", production=False)
    check(any("not a whole number of frames" in w for w in pl.warnings), "a duration between frames warns")
    wild = [{"id": "a", "template": "title", "duration": 3, "copy": {"head": "Hi"}},
            {"id": "b", "template": "title", "duration": 3, "copy": {"head": "Yo"}, "transitionIn": {"type": "wipe"}}]
    check(any("outside the concept" in e for e in vd.plan(None, "t", piece(wild), AD, "social-9x16", True).errors),
          "a transition outside the concept fails production")
    check(any("outside the concept" in w for w in vd.plan(None, "t", piece(wild), AD, "social-9x16", False).warnings),
          "and is only a warning in a draft")
    ph = [{"id": "a", "template": "title", "duration": 4, "copy": {"head": "REPLACE: the promise"}}]
    check(any("placeholder" in e for e in vd.plan(None, "t", piece(ph), AD, "social-9x16", True).errors),
          "placeholder copy fails production")
    wordy = [{"id": "a", "template": "title", "duration": 3,
              "copy": {"head": "A very long headline that nobody could read in the time this scene stays still on screen"}}]
    pl = vd.plan(None, "t", piece(wordy), AD, "social-9x16", True)
    check(any(r["id"] == "reading:a" for r in pl.reviews) and not pl.errors, "too many words is a review item, not a failure")
    long_ = [{"id": "a", "template": "title", "duration": 60, "copy": {"head": "x"}},
             {"id": "b", "template": "title", "duration": 40, "copy": {"head": "y"}}]
    check(any("this format takes" in e for e in vd.plan(None, "t", piece(long_), AD, "social-9x16", False).errors),
          "a piece longer than the format allows fails")


def caption_checks() -> None:
    sc = [{"id": "a", "template": "title", "duration": 4, "copy": {"head": "Hi"}, "vo": "One two three four five six seven eight."},
          {"id": "b", "template": "title", "duration": 2, "copy": {"head": "Yo"}, "transitionIn": {"type": "cut"},
           "vo": "This line is far too long for a two second scene, by quite a lot of words."}]
    p_ = piece(sc)
    pl = vd.plan(None, "t", p_, AD, "social-9x16", False)
    cues, errors, reviews = vd.cues(pl, p_, AD)
    check(len(cues) == 2 and cues[0]["start"] == 0.15 and abs(cues[0]["end"] - (0.15 + 8 / 150 * 60)) < 0.002,
          f"planned voice-over timing ({cues[0]['start']}-{cues[0]['end']})")
    check(cues[1]["start"] >= cues[0]["end"], "a line never starts over the previous one")
    check(any(r["id"] == "vo-fit:b" for r in reviews), "a line longer than its scene is a review item")
    check(any("after the video" in e for e in errors), "a voice-over ending after the video fails")
    srt = vd.srt(cues)
    check(srt.startswith("1\n00:00:00,150 --> ") and "\n\n2\n" in srt, "SRT numbering and comma timestamps")
    vtt = vd.vtt(cues)
    check(vtt.startswith("WEBVTT") and "NOTE planned timing" in vtt and "00:00:00.150 --> " in vtt, "VTT header says planned")
    check(all(len(line) <= 32 for c in cues for s in c["subtitles"] for line in s["lines"]), "subtitle lines wrap at 32 characters")


def signal_checks() -> None:
    w = 16 * 16
    black, white, grey = bytes(w), bytes([255]) * w, bytes([128]) * w
    strobe = [black if (i // 3) % 2 == 0 else white for i in range(60)]  # 5 Hz at 30 fps
    check(bool(framecheck.flash_signal(strobe, 30)), "a 5 Hz full-frame strobe is flagged")
    slow = [bytes([min(255, i * 4)]) * w for i in range(60)]
    check(not framecheck.flash_signal(slow, 30), "a slow fade is not flagged")
    check(not framecheck.flash_signal([grey] * 30, 30), "a still frame is not flagged")
    info = {"streams": [{"codec_type": "video", "codec_name": "h264", "profile": "High", "pix_fmt": "yuv420p",
                         "color_space": "bt709", "color_primaries": "bt709", "color_transfer": "bt709",
                         "width": 1080, "height": 1920, "r_frame_rate": "30/1", "nb_read_frames": "90"}]}
    tmp = Path(os.environ.get("TMPDIR") or os.environ.get("TEMP") or "/tmp") / f"fs-{os.getpid()}.mp4"
    tmp.write_bytes(b"\0\0\0\x20ftypisom" + b"moov" + b"\0" * 32 + b"mdat")
    try:
        check(ffm.check_profile(info, tmp, "h264-web", 90, (1080, 1920), 30) == [], "a file matching h264-web passes")
        bad = {"streams": [dict(info["streams"][0], color_primaries=None, nb_read_frames="89", pix_fmt="yuv444p")]}
        probs = ffm.check_profile(bad, tmp, "h264-web", 90, (1080, 1920), 30)
        check(len(probs) == 3, f"untagged primaries, a missing frame and the wrong pixel format each fail ({probs})")
        tmp.write_bytes(b"\0\0\0\x20ftypisom" + b"mdat" + b"\0" * 32 + b"moov")
        check(any("faststart" in x for x in ffm.check_profile(info, tmp, "h264-web", 90, (1080, 1920), 30)),
              "moov after mdat fails the faststart rule")
    finally:
        tmp.unlink(missing_ok=True)


def token_checks() -> None:
    doc = {"motion": {"ok": {"$type": "cubicBezier", "$value": [0.2, 0, 0, 1]},
                      "over": {"$type": "cubicBezier", "$value": [0.34, 1.56, 0.64, 1]},
                      "bad": {"$type": "cubicBezier", "$value": [1.2, 0, 0, 1]},
                      "short": {"$type": "cubicBezier", "$value": [0.2, 0, 1]}}}
    t = dtcg.Tokens(doc, "t")
    check(t.resolve("motion.ok").value == [0.2, 0, 0, 1] and t.resolve("motion.over").value[1] == 1.56,
          "cubicBezier tokens resolve (y may overshoot)")
    errs = t.check_all()
    check(len(errs) == 2 and all("cubicBezier" in e for e in errs), "x outside 0..1 or the wrong length is refused")


def ffmpeg_lookup() -> None:
    saved = (ffm.shutil.which, os.environ.pop("FFMPEG", None))
    ffm.shutil.which = lambda name: None
    msgs = []
    try:
        for explicit in ("/nonexistent/ffmpeg", None):
            try:
                ffm.find_ffmpeg(explicit)
                msgs.append("")
            except OperationalError as e:
                msgs.append(str(e))
    finally:
        ffm.shutil.which = saved[0]
        if saved[1] is not None:
            os.environ["FFMPEG"] = saved[1]
    check("--ffmpeg /nonexistent/ffmpeg: no such file" in msgs[0], f"a wrong --ffmpeg path is an error, not ignored ({msgs[0][:70]})")
    check("not found" in msgs[1] and "--ffmpeg" in msgs[1], f"a missing ffmpeg is an operational error with install advice ({msgs[1][:70]})")


def main() -> int:
    websocket_checks()
    plan_checks()
    caption_checks()
    signal_checks()
    token_checks()
    ffmpeg_lookup()
    print(f"video library: {failed} failure(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
