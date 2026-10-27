#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Finish a verified local S31 update without weakening crash recovery.

The caller has already verified the selected application, protected metadata and
MAC, then requested esptool's native watchdog reset. Wait for that build's safe
first boot before ONE ordinary USB reset. Never retry a reset, clear recovery
records, or send a command to the application.
"""
from __future__ import annotations

import codecs
import os
from pathlib import Path
import re
import select
import time


class RestartError(RuntimeError):
    pass


class BootEvidence:
    """Bounded complete-line parser; admits only the expected boot and build."""
    def __init__(self, version: str, elf: str, first: bool):
        if not re.fullmatch(r"[0-9a-f]{64}", elf):
            raise RestartError("Expected a full verified application ELF digest")
        self.version, self.elf, self.first = version, elf, first
        self.pending = ""
        self.decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self.fields = {}
        self.reset_lines = 0
        self.rom_lines = 0
        self.ready = False
        self.bytes_seen = 0

    def feed(self, data: bytes):
        self.bytes_seen += len(data)
        if self.bytes_seen > 512 * 1024:
            raise RestartError("Startup console exceeded its bounded capture")
        self.pending += self.decoder.decode(data)
        while "\n" in self.pending:
            line, self.pending = self.pending.split("\n", 1)
            self.line(re.sub(r"\x1b\[[0-9;]*m", "", line).strip())
        if len(self.pending) > 4096:
            raise RestartError("Invalid oversized startup line")

    def line(self, line: str):
        if any(x in line for x in ("Guru Meditation", "panic'ed", "CPU_LOCKUP_RESET",
                                    "boot_state: checkpoint", "assert failed")):
            raise RestartError("A real startup failure was reported; retain protection")
        if line.startswith("ESP-ROM:"):
            self.rom_lines += 1
            if self.rom_lines > 1:
                raise RestartError("Unexpected repeated ROM startup")
        if line.startswith("rst:"):
            match = re.match(r"rst:0x([0-9a-fA-F]+)", line)
            allowed = (0x01, 0x10, 0x17) if self.first else (0x17,)
            if not match or int(match[1], 16) not in allowed or "SPI_FAST_FLASH_BOOT" not in line:
                raise RestartError("Unexpected reset/boot mode; retain protection")
            if "raw_reset" in self.fields:
                raise RestartError("Repeated raw reset record")
            self.fields["raw_reset"] = int(match[1], 16)
        for field, pattern in (
            ("project", r"app_init: Project name:\s*(\S+)"),
            ("version", r"app_init: App version:\s*(\S+)"),
            ("elf", r"app_init: ELF file SHA256:\s*([0-9a-f]+)"),
        ):
            match = re.search(pattern, line)
            if match:
                if field in self.fields:
                    raise RestartError("Repeated application startup")
                self.fields[field] = match[1]
                expected = {"project": "Kiikoread_Metalio_S31",
                            "version": self.version, "elf": self.elf}[field]
                matches = (expected.startswith(match[1]) and len(match[1]) >= 8) if field == "elf" else match[1] == expected
                if not matches:
                    raise RestartError("Startup build differs from verified application")
        match = re.search(r"read_pico: startup reset=(\d+)\b", line)
        if match:
            self.reset_lines += 1
            self.fields["reset"] = int(match[1])
            allowed = (1, 7, 11) if self.first else (11,)
            if self.reset_lines != 1 or self.fields["reset"] not in allowed:
                raise RestartError("Unexpected reset cause; retain protection")
            if "raw_reset" in self.fields and self.fields["raw_reset"] != {1: 1, 7: 16, 11: 23}[self.fields["reset"]]:
                raise RestartError("Inconsistent raw and SDK reset causes")
        match = re.search(r"boot_state: startup recovery=(\d+) resume=(\d+) reasons=0x([0-9a-fA-F]+)", line)
        if match:
            if "reasons" in self.fields:
                raise RestartError("Repeated startup protection record")
            recovery, resume, reasons = int(match[1]), int(match[2]), int(match[3], 16)
            self.fields.update(recovery=recovery, resume=resume, reasons=reasons)
            expected = (1, 0, 1) if self.first and self.fields.get("reset") == 7 else (0, 0, 0)
            if "reset" not in self.fields or (recovery, resume, reasons) != expected:
                raise RestartError("Another protection cause is present; do not reset it")
        if "app_loop: UI ready on " in line:
            required = {"project", "version", "elf", "reset", "recovery", "resume", "reasons"}
            if not required.issubset(self.fields):
                raise RestartError("Incomplete startup evidence; do not reset")
            self.ready = True


def _port_for_mac(mac: str) -> str:
    from serial.tools.list_ports import comports
    normalize = lambda x: (x or "").lower().replace(":", "").replace("-", "")
    expected = normalize(mac)
    if not re.fullmatch(r"[0-9a-f]{12}", expected):
        raise RestartError("Invalid approved MAC")
    matches = [p for p in comports()
               if p.vid == 0x303a and p.pid == 0x1001 and normalize(p.serial_number) == expected]
    if len(matches) != 1:
        raise RestartError("Approved S31 USB identity is absent or ambiguous")
    return matches[0].device


def capture_boot(mac: str, version: str, elf: str, first: bool,
                 output: Path, timeout: float = 30) -> dict:
    if os.name != "posix":
        raise RestartError("This local console verification requires POSIX; use a device-menu restart")
    evidence = BootEvidence(version, elf, first)
    fd = None
    deadline = time.monotonic() + timeout
    try:
        with output.open("xb", buffering=0) as log:
            while time.monotonic() < deadline:
                if fd is None:
                    try:
                        fd = os.open(_port_for_mac(mac), os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
                    except (OSError, RestartError):
                        time.sleep(.1)
                        continue
                try:
                    if not select.select([fd], [], [], .2)[0]:
                        continue
                    data = os.read(fd, 32768)
                except OSError:
                    os.close(fd)
                    fd = None
                    continue
                if not data:
                    os.close(fd)
                    fd = None
                    time.sleep(.1)
                    continue
                log.write(data)
                evidence.feed(data)
                if evidence.ready:
                    return evidence.fields
        raise RestartError("Safe startup was not confirmed before timeout; no further reset")
    finally:
        if fd is not None:
            os.close(fd)


def ordinary_usb_reset(mac: str):
    # The same control-line primitive used by Espressif's monitor/esptool.
    # POSIX open does not configure baud/DTR/RTS, avoiding an extra opening reset.
    import fcntl
    import struct
    import termios
    from esp_pylib.serial_reset import hard_reset

    port = _port_for_mac(mac)
    fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    class Lines:
        dtr = False
        def setDTR(self, value):
            self.change(termios.TIOCM_DTR, value)
            self.dtr = value
        def setRTS(self, value):
            self.change(termios.TIOCM_RTS, value)
        def change(self, mask, value):
            fcntl.ioctl(fd, termios.TIOCMBIS if value else termios.TIOCMBIC, struct.pack("I", mask))
    try:
        if _port_for_mac(mac) != port:
            raise RestartError("Approved USB identity changed before ordinary reset")
        lines = Lines()
        lines.setDTR(False)
        # One pulse only; unlike retrying ResetStrategy, no second reset on hotplug.
        hard_reset(lines, hold_delay=.2, post_release_delay=.2)
    finally:
        os.close(fd)


def finish_controlled_restart(mac: str, application: bytes, output: Path) -> dict:
    import struct
    if (len(application) < 256 or application[0] != 0xe9 or
        struct.unpack_from("<H", application, 12)[0] != 32 or
        struct.unpack_from("<I", application, 32)[0] != 0xabcd5432 or
        application[80:112].split(b"\0")[0] != b"Kiikoread_Metalio_S31"):
        raise RestartError("Invalid verified S31 application identity")
    version = application[48:80].split(b"\0")[0].decode("ascii")
    elf = application[176:208].hex()
    first = capture_boot(mac, version, elf, True, output / "controlled-first-boot.log")
    if first["recovery"] == 0:
        # Some S31 reset paths already report POWERON/USB and retain no protection.
        # Verify that complete clean boot and avoid an unnecessary second reset.
        return {"method": "native-watchdog-verified-clean-boot", "first_boot": first,
                "final_boot": first, "device_boot_verified": True,
                "recovery_protection_retained": True}
    print("S31_STAGE: Verified safe update boot; ordinary USB restart", flush=True)
    ordinary_usb_reset(mac)
    final = capture_boot(mac, version, elf, False, output / "controlled-final-boot.log")
    return {"method": "native-watchdog-safe-boot-then-ordinary-USB-reset",
            "first_boot": first, "final_boot": final, "device_boot_verified": True,
            "recovery_protection_retained": True}

