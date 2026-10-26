"""Sandbox data snapshot (OD-03 / OD-03a): the app never opens the repository's working-tree data/.

On start the checksum-verified backup of legacy.sqlite3 is copied into runtime/ and opened READ-ONLY. If the source checksum does not
match the expected value the app refuses to start, so every number on screen comes from the known synthetic baseline (seed 4100).
"""
import hashlib
import os
import pathlib
import shutil
import sqlite3
import threading


class SnapshotError(Exception):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Snapshot(object):
    def __init__(self, source, expected_sha256, runtime_dir):
        if not os.path.exists(source):
            raise SnapshotError("data source not found: %s (set paths.data_source in config/settings.json)" % source)
        got = sha256_file(source)
        if expected_sha256 and got != expected_sha256:
            raise SnapshotError("data source checksum mismatch: expected %s, got %s" % (expected_sha256[:12], got[:12]))
        os.makedirs(runtime_dir, exist_ok=True)
        self.path = os.path.join(runtime_dir, "legacy-snapshot.sqlite3")
        if not os.path.exists(self.path) or sha256_file(self.path) != got:
            shutil.copyfile(source, self.path)
        self.source, self.sha256 = source, got
        self._local = threading.local()

    def con(self):
        c = getattr(self._local, "con", None)
        if c is None:
            uri = pathlib.Path(self.path).resolve().as_uri() + "?mode=ro"
            c = sqlite3.connect(uri, uri=True, check_same_thread=False)
            self._local.con = c
        return c

    def q(self, sql, params=()):
        return list(self.con().execute(sql, params))
