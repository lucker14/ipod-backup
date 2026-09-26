import tempfile
import unittest
from pathlib import Path

import ipod_backup


def mp3_with_tags(title, artist):
    frames = []
    for frame_id, value in ((b"TIT2", title), (b"TPE1", artist)):
        text = b"\x03" + value.encode("utf-8")
        frames.append(frame_id + len(text).to_bytes(4, "big") + b"\x00\x00" + text)
    tag = b"".join(frames)
    size = bytes(
        (
            (len(tag) >> 21) & 0x7F,
            (len(tag) >> 14) & 0x7F,
            (len(tag) >> 7) & 0x7F,
            len(tag) & 0x7F,
        )
    )
    return b"ID3\x03\x00\x00" + size + tag + b"\xff\xfb audio"


def mp4_atom(atom_type, payload):
    return (len(payload) + 8).to_bytes(4, "big") + atom_type + payload


def m4a_with_tags(title, artist):
    def metadata_item(atom_type, value):
        data_atom = mp4_atom(b"data", b"\x00\x00\x00\x01\x00\x00\x00\x00" + value.encode())
        return mp4_atom(atom_type, data_atom)

    ilst = mp4_atom(
        b"ilst",
        metadata_item(b"\xa9nam", title) + metadata_item(b"\xa9ART", artist),
    )
    meta = mp4_atom(b"meta", b"\x00\x00\x00\x00" + ilst)
    return mp4_atom(b"moov", mp4_atom(b"udta", meta))


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "device" / "iPod_Control"
        self.destination = self.root / "backup"
        (self.source / "Music" / "F00").mkdir(parents=True)
        (self.source / "iTunes").mkdir()
        (self.source / "Music" / "F00" / "ABCD.mp3").write_bytes(b"track data")
        (self.source / "iTunes" / "iTunesDB").write_bytes(b"library data")

    def tearDown(self):
        self.temporary.cleanup()

    def test_volume_root_resolves_to_ipod_control(self):
        self.assertEqual(
            ipod_backup.resolve_source(self.source.parent),
            self.source.resolve(),
        )

    def test_resolves_trailing_shell_prompt_marker(self):
        volume = self.root / "IPOD UªÍVAT"
        volume.mkdir()
        self.assertEqual(ipod_backup.resolve_source(Path(f"{volume}$")), volume.resolve())

    def test_keeps_trailing_dollar_when_path_exists(self):
        volume = self.root / "volume$"
        volume.mkdir()
        self.assertEqual(ipod_backup.resolve_source(volume), volume.resolve())

    def test_backup_and_compare(self):
        self.assertEqual(ipod_backup.backup(self.source, self.destination, 2, False), 0)
        self.assertEqual(ipod_backup.compare(self.source, self.destination, True), 0)
        self.assertEqual(
            (self.destination / "Music" / "F00" / "ABCD.mp3").read_bytes(),
            b"track data",
        )

    def test_compare_reports_missing_and_extra_without_deleting(self):
        self.destination.mkdir()
        (self.destination / "old-file").write_bytes(b"keep me")
        self.assertEqual(ipod_backup.compare(self.source, self.destination, False), 1)
        self.assertTrue((self.destination / "old-file").exists())

    def test_deep_compare_detects_same_size_changes(self):
        self.assertEqual(ipod_backup.backup(self.source, self.destination, 1, False), 0)
        track = self.destination / "Music" / "F00" / "ABCD.mp3"
        track.write_bytes(b"TRACK DATA")
        self.assertEqual(ipod_backup.compare(self.source, self.destination, False), 0)
        self.assertEqual(ipod_backup.compare(self.source, self.destination, True), 1)

    def test_overlapping_paths_are_rejected(self):
        with self.assertRaises(ValueError):
            ipod_backup.ensure_disjoint(self.source, self.source / "backup")

    def test_organize_renames_from_id3_and_resumes(self):
        track = self.destination / "Music" / "F00" / "X7.mp3"
        track.parent.mkdir(parents=True)
        track.write_bytes(mp3_with_tags("Song Name", "The Band"))
        untagged = track.parent / "X8.mp3"
        untagged.write_bytes(b"no embedded tags")

        self.assertEqual(ipod_backup.organize(self.destination, 2), 0)
        named = track.parent / "The Band - Song Name.mp3"
        self.assertTrue(named.exists())
        self.assertTrue(untagged.exists())
        self.assertEqual(ipod_backup.organize(self.destination, 2), 0)
        self.assertTrue(named.exists())

    def test_organize_preserves_compare_and_backup_resume(self):
        original = self.source / "Music" / "F00" / "opaque.mp3"
        original.write_bytes(mp3_with_tags("Tagged Song", "Artist"))
        self.assertEqual(ipod_backup.backup(self.source, self.destination, 2, False), 0)
        self.assertEqual(ipod_backup.organize(self.destination, 2), 0)
        self.assertEqual(ipod_backup.compare(self.source, self.destination, True), 0)

        self.assertEqual(ipod_backup.backup(self.source, self.destination, 2, True), 0)
        self.assertFalse((self.destination / "Music" / "F00" / "opaque.mp3").exists())
        self.assertTrue(
            (self.destination / "Music" / "F00" / "Artist - Tagged Song.mp3").exists()
        )

    def test_organize_reads_mp4_tags_and_suffixes_collisions(self):
        folder = self.destination / "Music" / "F00"
        folder.mkdir(parents=True)
        for filename in ("X1.m4a", "X2.m4a"):
            (folder / filename).write_bytes(m4a_with_tags("Song", "Band"))

        self.assertEqual(ipod_backup.organize(self.destination, 2), 0)
        self.assertTrue((folder / "Band - Song.m4a").exists())
        self.assertTrue((folder / "Band - Song (2).m4a").exists())


if __name__ == "__main__":
    unittest.main()
