#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Guard real recovery causes and USB state around a controlled S31 update."""
import struct
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import s31_controlled_restart as restart

VERSION = "0.3.3-rc105"
ELF = "abcdef123" + "0" * 55


def transcript(first=True, reason=None):
    reset, raw, recovery = (7, "10", 1) if first else (11, "17", 0)
    causes = (1 if first else 0) if reason is None else reason
    return (
        "ESP-ROM:esp32s31-20251218\r\n"
        f"rst:0x{raw} (TEST_RESET),boot:0x58 (SPI_FAST_FLASH_BOOT)\r\n"
        "I (1480) app_init: Project name:     Kiikoread_Metalio_S31\r\n"
        f"I (1480) app_init: App version:      {VERSION}\r\n"
        f"I (1480) app_init: ELF file SHA256:  {ELF[:9]}...\r\n"
        f"I (1489) read_pico: startup reset={reset} stack=11204\r\n"
        f"I (1520) boot_state: startup recovery={recovery} resume=0 reasons=0x{causes:02x}\r\n"
        "I (3954) ttf_font: stream /sdcard/fonts/仓耳云黑.ttf\r\n"
        "I (5498) app_loop: UI ready on 首页 Home\r\n"
    ).encode()


def application():
    data = bytearray(256)
    data[0] = 0xe9
    struct.pack_into("<H", data, 12, 32)
    struct.pack_into("<I", data, 32, 0xabcd5432)
    data[48:80] = VERSION.encode().ljust(32, b"\0")
    data[80:112] = b"Kiikoread_Metalio_S31".ljust(32, b"\0")
    data[176:208] = bytes.fromhex(ELF)
    return bytes(data)


class BootGuards(unittest.TestCase):
    def test_complete_boot_at_all_byte_boundaries(self):
        for first in (True, False):
            raw = transcript(first)
            for size in (1, 2, 31, len(raw)):
                with self.subTest(first=first, size=size):
                    evidence = restart.BootEvidence(VERSION, ELF, first)
                    for start in range(0, len(raw), size):
                        evidence.feed(raw[start:start + size])
                    self.assertTrue(evidence.ready)
                    self.assertEqual(evidence.fields["recovery"], int(first))

    def test_real_causes_and_old_ambiguous_diagnostics_never_admit(self):
        for reason in (2, 3, 4, 5, 8, 9, 16, 17, 31):
            with self.subTest(reason=reason), self.assertRaises(restart.RestartError):
                restart.BootEvidence(VERSION, ELF, True).feed(transcript(reason=reason))
        raw = transcript().replace(b" reasons=0x01", b"")
        with self.assertRaises(restart.RestartError):
            restart.BootEvidence(VERSION, ELF, True).feed(raw)

    def test_wrong_build_reset_repeated_start_and_failure_are_rejected(self):
        raw = transcript()
        broken = [
            raw.replace(b"Kiikoread_Metalio_S31", b"Other_Project"),
            raw.replace(VERSION.encode(), b"0.3.3-rc104"),
            raw.replace(ELF[:9].encode(), b"012345678"),
            raw.replace(b"startup reset=7", b"startup reset=3"),
            raw.replace(b"rst:0x10", b"rst:0x1a"),
            raw.replace(b"SPI_FAST_FLASH_BOOT", b"DOWNLOAD_BOOT"),
            raw.replace(b"recovery=1", b"recovery=0"),
            raw.replace(b"resume=0", b"resume=1"),
            raw + b"ESP-ROM:esp32s31-20251218\n",
            raw.replace(b"I (5498)", b"W (5490) boot_state: checkpoint: ERROR\nI (5498)"),
            raw.replace(b"I (5498)", b"Guru Meditation Error: Core 0 panic'ed\nI (5498)"),
        ]
        for i, value in enumerate(broken):
            with self.subTest(i=i), self.assertRaises(restart.RestartError):
                restart.BootEvidence(VERSION, ELF, True).feed(value)

    def test_incomplete_start_never_admits_and_noise_is_bounded(self):
        evidence = restart.BootEvidence(VERSION, ELF, True)
        evidence.feed(transcript().split(b"I (5498)")[0])
        self.assertFalse(evidence.ready)
        for raw in (b"x" * 4097, b"x\n" * (256 * 1024 + 1)):
            with self.assertRaises(restart.RestartError):
                restart.BootEvidence(VERSION, ELF, True).feed(raw)

    def test_successful_handoff_resets_once_after_first_ready(self):
        calls = []
        def capture(mac, version, elf, first, path):
            self.assertEqual((mac, version, elf), ("1c:29:04:d0:2a:42", VERSION, ELF))
            calls.append("first" if first else "final")
            return {"recovery": int(first), "reasons": int(first)}
        with patch.object(restart, "capture_boot", capture), \
             patch.object(restart, "ordinary_usb_reset", side_effect=lambda _mac: calls.append("reset")):
            report = restart.finish_controlled_restart("1c:29:04:d0:2a:42", application(), Path("/unused"))
        self.assertEqual(calls, ["first", "reset", "final"])
        self.assertTrue(report["device_boot_verified"])

    def test_first_failure_never_resets_final_failure_is_not_success(self):
        for stage in ("first", "reset", "final"):
            calls = []
            def capture(_mac, _version, _elf, first, _path):
                name = "first" if first else "final"
                calls.append(name)
                if name == stage:
                    raise restart.RestartError("real failure")
                return {"recovery": 1}
            def reset(_mac):
                calls.append("reset")
                if stage == "reset":
                    raise OSError("disconnect")
            with patch.object(restart, "capture_boot", capture), \
                 patch.object(restart, "ordinary_usb_reset", reset), \
                 self.assertRaises((restart.RestartError, OSError)):
                restart.finish_controlled_restart("1c:29:04:d0:2a:42", application(), Path("/unused"))
            expected = ["first", "reset", "final"]
            self.assertEqual(calls, expected[:expected.index(stage) + 1])

    def test_invalid_image_never_opens_console(self):
        for pos in (0, 12, 32, 80):
            raw = bytearray(application())
            raw[pos] ^= 1
            with patch.object(restart, "capture_boot") as capture, \
                 patch.object(restart, "ordinary_usb_reset") as reset, \
                 self.assertRaises(restart.RestartError):
                restart.finish_controlled_restart("1c:29:04:d0:2a:42", raw, Path("/unused"))
            capture.assert_not_called()
            reset.assert_not_called()

    def test_clean_first_poweron_or_usb_boot_skips_second_reset(self):
        for sdk, raw in ((1, "01"), (11, "17")):
            value = transcript(False).replace(b"startup reset=11", f"startup reset={sdk}".encode()).replace(b"rst:0x17", f"rst:0x{raw}".encode())
            evidence = restart.BootEvidence(VERSION, ELF, True)
            evidence.feed(value)
            self.assertTrue(evidence.ready)
            with patch.object(restart, "capture_boot", return_value=evidence.fields) as capture, \
                 patch.object(restart, "ordinary_usb_reset") as reset:
                result = restart.finish_controlled_restart("1c:29:04:d0:2a:42", application(), Path("/unused"))
            capture.assert_called_once()
            reset.assert_not_called()
            self.assertTrue(result["device_boot_verified"])

    def test_usb_identity_survives_path_change_but_rejects_other_or_duplicate_device(self):
        def port(serial, path="/dev/cu.usbmodem1401", vid=0x303a, pid=0x1001):
            return SimpleNamespace(device=path, vid=vid, pid=pid, serial_number=serial)
        wanted = port("1C:29:04:D0:2A:42", "/dev/cu.usbmodem1403")
        with patch("serial.tools.list_ports.comports", return_value=[wanted, port("000000000000")]):
            self.assertEqual(restart._port_for_mac("1c:29:04:d0:2a:42"), wanted.device)
        for found in ([], [port("000000000000")], [wanted, wanted],
                      [port("1c2904d02a42", vid=0x1234)]):
            with patch("serial.tools.list_ports.comports", return_value=found), \
                 self.assertRaises(restart.RestartError):
                restart._port_for_mac("1c:29:04:d0:2a:42")

    def test_capture_timeout_and_parser_failure_close_descriptor(self):
        for data in (None, b"Guru Meditation Error: Core 0 panic'ed\n"):
            with tempfile.TemporaryDirectory() as folder, \
                 patch.object(restart, "_port_for_mac", return_value="/dev/test"), \
                 patch.object(restart.os, "open", return_value=100) as opened, \
                 patch.object(restart.os, "close") as closed, \
                 patch.object(restart.time, "monotonic", side_effect=[0, .01, 31]), \
                 patch.object(restart.select, "select", return_value=([100], [], []) if data else ([], [], [])), \
                 patch.object(restart.os, "read", return_value=data), \
                 self.assertRaises(restart.RestartError):
                restart.capture_boot("1c:29:04:d0:2a:42", VERSION, ELF, True, Path(folder) / "boot.log")
            opened.assert_called_once()
            closed.assert_called_once_with(100)


if __name__ == "__main__":
    unittest.main(verbosity=2)

