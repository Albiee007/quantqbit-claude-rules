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


def format_checks() -> None:
    for name, f in vd.FORMATS.items():
        w, h = f["size"]
        ok = all(s["left"] + s["right"] < w * 0.5 and s["top"] + s["bottom"] < h * 0.5 and w % 2 == 0 and h % 2 == 0
                 for s in f["safe"].values()) and f["safe"]["strict"]["top"] >= f["safe"]["standard"]["top"]
        check(ok, f"{name}: even size, safe insets leave most of the frame, strict is stricter")
    sc = [{"id": "a", "template": "title", "duration": 3, "copy": {"head": "Hi", "sub": "A long subtitle line"},
           "byFormat": {"social-1x1": {"layout": "type-lower", "hide": ["sub"]}, "wide-16x9": {"copy": {"head": "Hello"}}}},
          {"id": "b", "template": "stat", "duration": 3, "copy": {"value": "3x", "label": "faster"}, "transitionIn": {"type": "fade"}}]
    p_ = dict(piece(sc), formats=["social-9x16", "social-1x1", "wide-16x9"])
    plans = {f: vd.plan(None, "t", p_, AD, f, False) for f in p_["formats"]}
    check(len({(pl.frames, tuple((s.start, s.frames) for s in pl.scenes)) for pl in plans.values()}) == 1,
          "every format of a piece shares one timeline")
    a1, aw = plans["social-1x1"].scenes[0], plans["wide-16x9"].scenes[0]
    check(a1.layout == "type-lower" and "sub" not in a1.copy and aw.copy["head"] == "Hello" and aw.copy["sub"],
          "byFormat changes layout, hides and replaces copy for that format only")
    check(plans["social-9x16"].scenes[0].copy["sub"] and plans["social-9x16"].scenes[0].layout == "type-start",
          "other formats keep the authored scene")
    hidden = [{"id": "a", "template": "title", "duration": 3, "copy": {"head": "Hi"}, "byFormat": {"social-1x1": {"hide": ["head"]}}}]
    check(any("hidden in social-1x1" in e for e in vd.plan(None, "t", dict(piece(hidden), formats=["social-9x16", "social-1x1"]),
                                                            AD, "social-1x1", False).errors),
          "hiding copy a template needs fails, naming the format")
    ad = dict(AD, sceneTemplates=AD["sceneTemplates"] + ["still"])
    st = [{"id": "s", "template": "still", "duration": 3}]
    check(any("needs media.image" in e for e in vd.plan(None, "t", piece(st), ad, "social-9x16", False).errors),
          "a still scene needs a picture")
    st = [{"id": "s", "template": "still", "duration": 3, "media": {"image": "art/x.png", "motion": "push-in"}}]
    pl = vd.plan(None, "t", piece(st), ad, "social-9x16", True)
    check(not pl.errors and pl.scenes[0].media["motion"] == "push-in" and any(r["id"] == "provenance:s" for r in pl.reviews),
          "a still scene plans, and a picture outside brand/ with no licence is a provenance review item")
    check(any("outside the concept" in e for e in vd.plan(None, "t", piece(st), AD, "social-9x16", True).errors),
          "still scenes are opted in by the concept (sceneTemplates)")
    lp = dict(piece([{"id": "a", "template": "title", "duration": 20, "copy": {"head": "Hi"}}]), kind="loop")
    check(any("loops take up to" in e for e in vd.plan(None, "t", lp, AD, "social-9x16", False).errors),
          "a GIF/WebP loop longer than 15 s fails")
    lp = dict(piece([{"id": "a", "template": "title", "duration": 4, "copy": {"head": "Hi"}}]), loop={"fps": 12},
              poster={"scene": "zz"})
    errs = vd.plan(None, "t", lp, AD, "social-9x16", False).errors
    check(any("does not divide" in e for e in errs) and any("poster.scene" in e for e in errs),
          "a loop rate that does not divide the fps, and an unknown poster scene, fail")
    check(vd.loop_spec(dict(piece([]), kind="loop")) == vd.LOOP_DEFAULT and vd.loop_spec(piece([])) is None,
          "a loop piece gets a GIF by default; a social piece no loop")
    check(vd.loop_spec(dict(piece([], fps=24), kind="loop"))["fps"] == 12 and
          vd.loop_spec(dict(piece([], fps=25), kind="loop"))["fps"] == 5, "the default loop rate divides 24 and 25 fps too")
    odd = dict(piece([{"id": "a", "template": "title", "duration": 91 / 30, "copy": {"head": "Hi"}}]), kind="loop")
    check(any("whole number of loop frames" in e for e in vd.plan(None, "t", odd, AD, "social-9x16", False).errors),
          "a loop whose length is not whole loop frames fails (its last frame would hold too long)")
    m18 = {"schemaVersion": 1, "id": "t", "kind": "social", "formats": ["social-9x16"], "fps": 30,
           "scenes": [{"id": "a", "template": "title", "duration": 3, "copy": {"head": "Hi"}, "vo": "Hello."},
                      {"id": "b", "template": "stat", "duration": 3, "copy": {"value": "3x"},
                       "transitionIn": {"type": "fade", "duration": 0.5}}], "voice": {"language": "en"}}
    check(vd._parts(m18, {}) == {"visual": "2d5f31c38832f9275a8b944f8ba37b3f6a9c971a8716d94fb7267243c42eeb3b",
                                 "timing": "47f6dd7b93636e5023a5d924af2d4826995bfaac01daa0ca506430a276acc6d6",
                                 "script": "829717203ccbba24b8dd47d27b3c0c6a1cada2479f431056377acbf37e585223"},
          "a 1.8 piece hashes as in 1.8 (its storyboard approval stays valid)")
    with_media = vd._parts(dict(m18, scenes=m18["scenes"] + [{"id": "s", "template": "still", "duration": 3,
                                                               "media": {"image": "brand/a.png"}}]), {"brand/a.png": "0" * 64})
    other = vd._parts(dict(m18, scenes=m18["scenes"] + [{"id": "s", "template": "still", "duration": 3,
                                                          "media": {"image": "brand/a.png"}}]), {"brand/a.png": "1" * 64})
    check("media" in with_media and with_media["media"] != other["media"] and with_media["visual"] == other["visual"],
          "the bytes of a picture are their own part of the storyboard hash")


def loop_checks() -> None:
    w = 16 * 16
    ramp = [bytes([i * 8]) * w for i in range(30)]
    seam, limit = framecheck.seam_signal(ramp)
    check(seam > limit, f"a loop that ends far from its start has a seam ({seam:.0f} > {limit:.0f})")
    tri = [bytes([abs(15 - i) * 8]) * w for i in range(30)]
    seam, limit = framecheck.seam_signal(tri)
    check(seam <= limit, f"a loop that returns to its start has none ({seam:.0f} <= {limit:.0f})")
    from PIL import Image
    tmp = Path(os.environ.get("TMPDIR") or os.environ.get("TEMP") or "/tmp")
    ims = [Image.new("RGB", (48, 24), (i * 30, 40, 90)) for i in range(6)] + [Image.new("RGB", (48, 24), (150, 40, 90))] * 2
    gif, webp, png = tmp / f"lp-{os.getpid()}.gif", tmp / f"lp-{os.getpid()}.webp", tmp / f"lp-{os.getpid()}.png"
    try:
        ims[0].save(gif, save_all=True, append_images=ims[1:], duration=100, loop=0)
        ims[0].save(webp, "WEBP", save_all=True, append_images=ims[1:], duration=100, loop=0)
        ims[0].save(png)
        check(framecheck.anim_problems(gif, "gif", 8, (48, 24), 0.8)[0] == [], "a looping GIF of the asked size and length passes")
        check(framecheck.anim_problems(webp, "webp-anim", 8, (48, 24), 0.8)[0] == [],
              "an animated WebP passes even when identical frames were merged")
        probs = framecheck.anim_problems(gif, "gif", 8, (64, 24), 2.0)[0]
        check(len(probs) == 2, f"the wrong size and length each fail ({probs})")
        ims[0].save(gif, save_all=True, append_images=ims[1:], duration=100)
        check(any("loop" in x for x in framecheck.anim_problems(gif, "gif", 8, (48, 24), 0.8)[0]), "a GIF that plays once fails")
        check(framecheck.anim_problems(png, "poster", 1, (48, 24), 0)[0] == [] and
              framecheck.anim_problems(png, "gif", 1, (48, 24), 0)[0], "a poster is a PNG of the format's size")
    finally:
        for f in (gif, webp, png):
            f.unlink(missing_ok=True)


def m3_checks() -> None:
    """App previews, recordings, transparency and recorded voice-over (1.11)."""
    ad = dict(AD, sceneTemplates=AD["sceneTemplates"] + ["recording"])
    rec = {"id": "r", "template": "recording", "duration": 13, "media": {"video": "brand/v/flow.mp4"}, "copy": {"head": "Plan"}}
    end = {"id": "e", "template": "end-card", "duration": 3, "copy": {"head": "Try it"}, "transitionIn": {"type": "fade"}}
    ap = dict(piece([rec, end]), kind="app-preview", formats=["app-preview-iphone"])
    pl = vd.plan(None, "t", ap, ad, "app-preview-iphone", True)
    check(not pl.errors and pl.scenes[0].media["video"] == "brand/v/flow.mp4",
          f"an app preview of a recording and an end card plans ({pl.errors})")
    check(any(r["id"] == "suitability:app-store:app-preview-iphone" and "e" in r["note"] for r in pl.reviews),
          "graphics scenes in an App Store preview are a suitability review item, not a failure")
    errs = vd.plan(None, "t", dict(ap, fps=25), ad, "app-preview-iphone", True).errors
    check(any("30 fps" in e for e in errs), "an App Store preview must run at 30 fps")
    short = dict(ap, scenes=[dict(rec, duration=8)])
    check(any("takes 15-30 s" in e for e in vd.plan(None, "t", short, ad, "app-preview-iphone", True).errors),
          "an App Store preview shorter than 15 s fails")
    norec = [{"id": "r", "template": "recording", "duration": 4}]
    check(any("needs media.video" in e for e in vd.plan(None, "t", piece(norec), ad, "social-9x16", False).errors),
          "a recording scene needs a recording")
    check(vd.output_profile(dict(piece([]), transparent=True), vd.FORMATS["wide-16x9"]) == "alpha-webm" and
          vd.output_profile(dict(piece([]), transparent=True, alpha="prores"), vd.FORMATS["wide-16x9"]) == "alpha-prores" and
          vd.output_profile(piece([]), vd.FORMATS["app-preview-ipad"]) == "app-preview",
          "transparent pieces encode with an alpha profile; app previews with the app-preview profile")
    tr = dict(piece([{"id": "a", "template": "title", "duration": 3, "copy": {"head": "Hi"}}]), transparent=True,
              loop={"outputs": ["gif"]}, audio={"voice": True})
    errs = vd.plan(None, "t", tr, AD, "social-9x16", False).errors
    check(any("can't keep the alpha" in e for e in errs) and any("carries no sound" in e for e in errs),
          "a transparent piece has no GIF loop and no sound")
    one = [{"id": "a", "template": "title", "duration": 4, "copy": {"head": "Hi"}, "vo": "One two three four five six."},
           {"id": "b", "template": "title", "duration": 3, "copy": {"head": "Yo"}, "transitionIn": {"type": "cut"}, "vo": "Bye now."}]
    p_ = piece(one)
    pl = vd.plan(None, "t", p_, AD, "social-9x16", False)
    cl, _, _ = vd.cues(pl, p_, AD, {"a": 1.25, "b": 0.8})
    check(cl[0]["end"] == round(cl[0]["start"] + 1.25, 3) and vd.caption_timing(cl) == "segment-aligned",
          "a recorded take sets its line's length (segment-aligned captions)")
    cl2, _, _ = vd.cues(pl, p_, AD, {"a": 1.25})
    check(vd.caption_timing(cl2) == "mixed" and "mixed timing" in vd.vtt(cl2), "takes for some lines only: mixed, and the VTT says so")
    long_, errs, _ = vd.cues(pl, p_, AD, {"b": 9.0})
    check(any("recorded voice-over ends" in e and "trim the take" in e for e in errs), "a take running past the video fails")
    check(ffm.PROFILES["app-preview"]["audio"] == "required" and ffm.PROFILES["alpha-webm"]["suffix"] == ".webm",
          "the app-preview profile requires a sound track; alpha WebM is a .webm")
    info = {"streams": [{"codec_type": "video", "codec_name": "h264", "profile": "High", "pix_fmt": "yuv420p",
                         "color_space": "bt709", "color_primaries": "bt709", "color_transfer": "bt709",
                         "width": 886, "height": 1920, "r_frame_rate": "30/1", "nb_read_frames": "480"}]}
    tmp = Path(os.environ.get("TMPDIR") or os.environ.get("TEMP") or "/tmp") / f"ap-{os.getpid()}.mp4"
    tmp.write_bytes(b"\0\0\0\x20ftypisom" + b"moov" + b"\0" * 32 + b"mdat")
    try:
        probs = ffm.check_profile(info, tmp, "app-preview", 480, (886, 1920), 30)
        check(probs == ["0 audio streams, want 1"], f"an app preview without a sound track fails ({probs})")
        info["streams"].append({"codec_type": "audio", "codec_name": "aac", "channels": 2, "sample_rate": "48000"})
        check(ffm.check_profile(info, tmp, "app-preview", 480, (886, 1920), 30) == [], "with a stereo AAC track it passes")
        check(any("lasts 32.00 s" in x for x in ffm.check_profile(info, tmp, "app-preview", 960, (886, 1920), 30)),
              "an app preview over 30 s fails")
        check(any("silent video" in x for x in ffm.check_profile(info, tmp, "h264-web", 480, (886, 1920), 30)),
              "a sound track in a video meant to be silent fails")
        alpha = {"streams": [{"codec_type": "video", "codec_name": "vp9", "pix_fmt": "yuv420p", "width": 960, "height": 540,
                              "r_frame_rate": "30/1", "nb_read_frames": "90", "tags": {"ALPHA_MODE": "1"}}]}
        check(ffm.check_profile(alpha, tmp, "alpha-webm", 90, (960, 540), 30) == [], "a VP9 track tagged alpha_mode=1 passes")
        alpha["streams"][0]["tags"] = {}
        check(any("no alpha" in x for x in ffm.check_profile(alpha, tmp, "alpha-webm", 90, (960, 540), 30)),
              "a VP9 track without alpha fails")
    finally:
        tmp.unlink(missing_ok=True)
    g, label = ffm._mix_graph([(0, 0.65), (1, 12.4)], (2, -18, True), 15.6)
    check("adelay=650|650" in g and "adelay=12400|12400" in g and "sidechaincompress" in g and "atrim=0:15.600" in g
          and label == "[mixed]", "the mix places each take at its line's start and ducks the music under the voice")
    check("[vor]apad,atrim=0:15.600[vo]" in g, "the voice bus lasts the whole video (the ducked music runs to the end)")
    g, _ = ffm._mix_graph([(0, -0.35)], None, 5.0)
    check("atrim=start=0.350,asetpts=PTS-STARTPTS,adelay=0|0" in g, "a take with more room tone than lead time is trimmed, not late")


def m4_checks() -> None:
    """Custom scenes, providers, word-aligned captions, the HyperFrames export (1.12)."""
    from harnesslib import hyperframes as hfx
    from harnesslib import providers as pvx
    tmp = Path(os.environ.get("TMPDIR") or os.environ.get("TEMP") or "/tmp") / f"m4-{os.getpid()}"
    (tmp / "s").mkdir(parents=True, exist_ok=True)
    try:
        good = tmp / "s" / "good.js"
        good.write_text("// no setTimeout here: a comment\nwindow.VideoScenes = {};\nVideoScenes.a = (el, ctx) => ctx.rand('x');\n"
                        "const svg = 'http://www.w3.org/2000/svg';\n", encoding="utf-8")
        bad = tmp / "s" / "bad.js"
        bad.write_text("const t = Date.now();\nrequestAnimationFrame(() => {});\nel.style.transition = 'x';\n"
                       "fetch('https://example.com/x.json');\nanim.play();\n", encoding="utf-8")
        check(vd.custom_code_problems(tmp, {"id": "a", "custom": {"script": "s/good.js"}}) == [],
              "a custom scene script without clocks, timers or network passes (comments and SVG namespaces aside)")
        probs = vd.custom_code_problems(tmp, {"id": "a", "custom": {"script": "s/bad.js"}})
        html = tmp / "s" / "page.html"
        html.write_text("<h2>Release Date</h2>\n<p>Updated daily // not a comment</p>\n<video src=\"a.mp4\" autoplay></video>\n"
                        "<div style=\"transition-duration: 2s\"></div>\n<img src=\"//cdn.example.com/x.png\">\n", encoding="utf-8")
        hp = vd.custom_code_problems(tmp, {"id": "a", "custom": {"html": "s/page.html", "script": "s/good.js"}})
        check(len(hp) == 3 and not any("a clock read" in x for x in hp) and any(":3:" in x for x in hp),
              f"in HTML, visible text is not code, while autoplay, transition-* and //cdn links are caught ({hp})")
        check(len(probs) == 5 and any("s/bad.js:1:" in x for x in probs), f"clocks, frame loops, transitions, network and playback each fail ({len(probs)})")
        ad = dict(AD, sceneTemplates=AD["sceneTemplates"] + ["custom"])
        cu = [{"id": "c", "template": "custom", "duration": 3}]
        check(any("needs custom.script" in e for e in vd.plan(None, "t", piece(cu), ad, "social-9x16", False).errors),
              "a custom scene needs a script")
        p_ = dict(piece([{"id": "c", "template": "custom", "duration": 3, "custom": {"script": "s/good.js"}}]),
                  libraries=[{"file": "lib/x.js", "name": "x", "license": "MIT"}])
        refs = {r for r, _, _ in vd.media_refs(p_)}
        check(refs == {"s/good.js", "lib/x.js"}, f"a custom scene's script and the libraries are part of the storyboard ({refs})")
        words = pvx.check_words({"words": [{"word": "Plan", "start": 0.5, "end": 0.8}, {"word": "ahead.", "start": 0.85, "end": 1.2}]}, 2.0)
        check(len(words) == 2, "a word alignment within the take is accepted")
        for bad_words in ({"words": []}, {"words": [{"word": "x", "start": 1.0, "end": 0.5}]},
                          {"words": [{"word": "x", "start": 0.5, "end": 3.0}]}):
            try:
                pvx.check_words(bad_words, 2.0)
                check(False, f"a broken alignment is refused ({bad_words})")
            except Exception:
                check(True, f"a broken alignment is refused ({str(bad_words)[:40]})")
        line = [{"id": "a", "template": "title", "duration": 4, "copy": {"head": "Hi"}, "vo": "Plan ahead."}]
        pp = piece(line)
        pl = vd.plan(None, "t", pp, AD, "social-9x16", False)
        cl, _, _ = vd.cues(pl, pp, AD, {"a": 0.7}, {"a": words}, {"a": 0.5})
        sub = cl[0]["subtitles"][0]
        check(cl[0]["timing"] == "word-aligned" and sub["start"] == round(cl[0]["start"] - 0.5 + 0.5, 3)
              and sub["end"] == round(cl[0]["start"] - 0.5 + 1.2, 3) and "word-aligned" in vd.vtt(cl),
              f"aligned words time each caption from its first word to its last ({sub})")
        from harnesslib import providers as pvq
        argv = pvq.argv_for("tts", {"command": ["prog", "{text}", "--c", "{casting}"]},
                            {"text": "{casting}", "casting": "x"})
        check(argv[1] == "{casting}" and argv[3] == "x", f"placeholders are filled in one pass ({argv})")
        frames_dir = tmp / "frames"
        frames_dir.mkdir()
        for n in (1, 2, 9, 10, 11):
            (frames_dir / f"frame_{n}.png").write_bytes(b"")
        order = [f.name for f in hfx.frame_files(frames_dir)]
        check(order == ["frame_1.png", "frame_2.png", "frame_9.png", "frame_10.png", "frame_11.png"],
              f"HyperFrames frames are read in frame order ({order})")
        build = tmp / "build"
        (build / "fonts").mkdir(parents=True)
        (build / "video.html").write_text('<head>\n<script src="timeline.js"></script>\n</head><body></body>', encoding="utf-8")
        (build / "timeline.js").write_text("//", encoding="utf-8")
        proj = hfx.export(build, tmp / "hfproj")
        html = (proj / "index.html").read_text(encoding="utf-8")
        check("timeline.js" not in html and not (proj / "timeline.js").exists() and (proj / "fonts").is_dir(),
              "the HyperFrames export is index.html with its assets and without our seek runtime")

        class S:
            def __init__(self, i, t):
                self.id, self.template = i, t
        try:
            hfx.refuse([S("a", "title"), S("b", "recording")])
            check(False, "HyperFrames refuses scenes that need our runtime")
        except Exception as e:
            check("b" in str(e) and "--engine ours" in str(e), "HyperFrames refuses scenes that need our runtime")
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


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


def custom_format_checks() -> None:
    from harnesslib.fsutil import InputError, canonical, sha256_text

    def rejects(custom: dict, fmt: str = "li") -> bool:
        try:
            vd.check_formats(dict(piece([]), formats=[fmt], customFormats=custom), "t")
        except InputError:
            return True
        return False

    li = {"li": {"size": "1200x628", "like": "og-card"}}
    spec = vd.format_spec(dict(piece([]), customFormats=li), "li")
    og = vd.FORMATS["og-card"]
    check(spec["size"] == (1200, 628) and spec["profile"] == og["profile"] and spec["typeScale"] == og["typeScale"]
          and (spec["min"], spec["max"]) == (og["min"], og["max"]), "a custom format inherits what it leaves out from its like")
    tall = vd.format_spec(dict(piece([]), customFormats={"t2": {"size": "2160x3840", "like": "social-9x16"}}), "t2")
    base = vd.FORMATS["social-9x16"]["safe"]["standard"]
    check(tall["safe"]["standard"] == {k: v * 2 for k, v in base.items()}, "safe insets scale with the size")
    wide = vd.format_spec(dict(piece([]), customFormats={"w": {"size": "2160x1080", "like": "social-1x1"}}), "w")
    sq = vd.FORMATS["social-1x1"]["safe"]["standard"]
    check(wide["safe"]["standard"]["left"] == sq["left"] * 2 and wide["safe"]["standard"]["top"] == sq["top"],
          "left and right scale by width, top and bottom by height")
    own = vd.format_spec(dict(piece([]), customFormats={"li": {"size": "1200x628", "like": "og-card",
                                                                "safe": {"strict": {"top": 100}}}}), "li")
    check(own["safe"]["strict"]["top"] == 100 and own["safe"]["strict"]["left"] == og["safe"]["strict"]["left"],
          "explicit insets are merged over the scaled ones")
    over = vd.format_spec(dict(piece([]), customFormats={"og-card": {"size": "800x420", "like": "og-card"}}), "og-card")
    check(over["size"] == (800, 420) and vd.FORMATS["og-card"]["size"] == (1200, 630),
          "a custom format may reuse a built-in id without changing the built-in")
    check(rejects({"li": {"size": "1201x628", "like": "og-card"}}), "an odd side is rejected")
    check(rejects({"li": {"size": "100x628", "like": "og-card"}}), "a side under 128 px is rejected")
    check(rejects({"li": {"size": "1200x628", "like": "li"}}), "like must name a built-in format")
    check(rejects({"li": {"size": "1200x628", "like": "og-card", "min": 20, "max": 10}}), "min must be under max")
    check(rejects({"li": {"size": "1200x628", "like": "og-card", "safe": {"standard": {"left": 700, "right": 600}}}}),
          "insets that leave no room are rejected")
    check(rejects({}, "nope"), "a format that is neither built in nor declared is rejected")
    sc = [{"id": "a", "template": "title", "duration": 3, "copy": {"head": "Hi"}, "byFormat": {"li": {"layout": "type-lower"}}}]
    p_ = dict(piece(sc), formats=["social-9x16", "li"], customFormats=li)
    vd.check_formats(p_, "t")
    pl = vd.plan(None, "t", p_, AD, "li", False)
    check(pl.scenes[0].layout == "type-lower" and vd.plan(None, "t", p_, AD, "social-9x16", False).scenes[0].layout == "type-start",
          "byFormat works for a custom format")
    stray = dict(piece([dict(sc[0], byFormat={"zz": {"layout": "type-lower"}})]))
    try:
        vd.check_formats(stray, "t")
        check(False, "a byFormat key that names no format is rejected")
    except InputError:
        check(True, "a byFormat key that names no format is rejected")
    plain = piece([{"id": "a", "template": "title", "duration": 3, "copy": {"head": "Hi"}}])
    visual_190 = {"kind": plain["kind"], "formats": plain["formats"],
                  "scenes": [{k: s.get(k) for k in ("id", "template", "layout", "background", "copy")} for s in plain["scenes"]]}
    check(vd._parts(plain)["visual"] == sha256_text(canonical(visual_190)),
          "a piece without customFormats hashes exactly as in 1.9.0 (existing approvals stay valid)")
    a = vd._parts(dict(plain, customFormats=li))["visual"]
    b = vd._parts(dict(plain, customFormats={"li": {"size": "1200x630", "like": "og-card"}}))["visual"]
    check(a != b and a != vd._parts(plain)["visual"], "changing a custom format changes the storyboard's visual hash")


def main() -> int:
    websocket_checks()
    plan_checks()
    format_checks()
    custom_format_checks()
    loop_checks()
    m3_checks()
    m4_checks()
    caption_checks()
    signal_checks()
    token_checks()
    ffmpeg_lookup()
    print(f"video library: {failed} failure(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
