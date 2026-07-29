# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
"""
Windows has no D-Bus session bus, so dbus-python isn't available there.
This module replaces the two things Variety uses D-Bus for on Linux -
detecting an already-running instance and forwarding it a command - with a
local loopback TCP socket. It mirrors the shape of the D-Bus calls made in
variety/__init__.py so the two code paths stay easy to compare.

A loopback socket has no notion of "session" the way the D-Bus session bus
does, so any local account on a shared machine could otherwise connect and
send commands. To close that gap, the primary instance writes a random
per-profile token to a file in the profile folder (readable only by the
current user's own files by default NTFS permissions) and every client must
present it before its command is processed.
"""
import hashlib
import json
import logging
import os
import secrets
import socket
import threading

logger = logging.getLogger("variety")

HOST = "127.0.0.1"


def _port_for_key(dbus_key):
    # Deterministic per-profile port, so different --profile instances don't collide.
    # Must be stable across separate processes, so plain hash() (randomized per
    # process since Python 3.3) would not work here.
    digest = hashlib.sha256(dbus_key.encode("utf-8")).hexdigest()
    return 40000 + (int(digest, 16) % 10000)


def _token_path():
    from variety.profile import get_profile_path

    return os.path.join(get_profile_path(), ".win_ipc_token")


def _get_or_create_token():
    path = _token_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            token = f.read().strip()
            if token:
                return token
    except OSError:
        pass
    token = secrets.token_hex(16)
    with open(path, "w", encoding="utf-8") as f:
        f.write(token)
    return token


def connect_to_running_instance(dbus_key):
    """
    Returns a connected socket if another instance is already listening,
    otherwise None (meaning this process should become the primary instance).
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        sock.connect((HOST, _port_for_key(dbus_key)))
        return sock
    except OSError:
        sock.close()
        return None


def send_command(sock, arguments):
    """Sends arguments to an already-connected running instance and returns its reply."""
    try:
        payload = _get_or_create_token().encode("utf-8") + b"\n" + json.dumps(arguments).encode(
            "utf-8"
        )
        sock.sendall(payload)
        sock.shutdown(socket.SHUT_WR)
        chunks = []
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks).decode("utf-8")
    finally:
        sock.close()


class WinIPCService:
    """
    Listens for commands from later Variety invocations, playing the same role
    as the D-Bus VarietyService object does on Linux.
    """

    def __init__(self, variety_window, dbus_key):
        self.variety_window = variety_window
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((HOST, _port_for_key(dbus_key)))
        self.server.listen(5)
        threading.Thread(target=self._serve_forever, daemon=True).start()

    def _serve_forever(self):
        while True:
            try:
                conn, _addr = self.server.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn):
        try:
            conn.settimeout(5)
            chunks = []
            while True:
                chunk = conn.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
            token, _, payload = b"".join(chunks).partition(b"\n")
            if token.decode("utf-8", errors="replace") != _get_or_create_token():
                logger.warning("Rejected Windows IPC command with invalid token")
                return
            arguments = json.loads(payload.decode("utf-8"))
            result = self.variety_window.process_command(arguments, initial_run=False)
            conn.sendall((result or "").encode("utf-8"))
        except Exception:
            logger.exception("Error handling command over the Windows IPC socket")
        finally:
            conn.close()
