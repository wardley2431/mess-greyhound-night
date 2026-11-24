from __future__ import annotations

import http.client
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import server


class VideoLibraryTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.videos = self.root / "videos"
        self.videos.mkdir()
        static_patch = patch.object(server, "STATIC_DIR", self.root)
        static_patch.start()
        self.addCleanup(static_patch.stop)
        self.state = server.new_event_state(seed=42, race_count=2)

    def add_file(self, name: str = "race01.mp4", data: bytes = b"sample video") -> Path:
        path = self.videos / name
        path.write_bytes(data)
        return path

    def ready_video(self) -> dict:
        self.add_file()
        server.sync_video_library(self.state)
        video = self.state["videoLibrary"][0]
        server.update_video(self.state, {"videoId": video["id"], "winningTrap": 4})
        return video

    def test_files_are_discovered_without_guessed_winners(self) -> None:
        self.add_file()
        self.add_file("race02.MP4")
        self.add_file("notes.txt")
        state = server.new_event_state(seed=42)
        self.assertEqual(len(state["videoLibrary"]), 2)
        self.assertEqual(state["videoLibrary"][0]["source"], "/videos/race01.mp4")
        self.assertIsNone(state["videoLibrary"][0]["winningTrap"])
        self.assertEqual(server.video_problem(state["videoLibrary"][0]), "Winning trap required")

    def test_sync_preserves_existing_titles_winners_and_ids(self) -> None:
        video = self.ready_video()
        video["title"] = "Original recording"
        before = video.copy()
        self.assertFalse(server.sync_video_library(self.state))
        self.assertEqual(self.state["videoLibrary"], [before])

    def test_encoded_filename_does_not_duplicate_manual_entry(self) -> None:
        self.add_file("Race 01.mp4")
        server.add_video(self.state, {
            "title": "First race", "source": "/videos/Race 01.mp4", "winningTrap": 2,
        })
        server.sync_video_library(self.state)
        self.assertEqual(len(self.state["videoLibrary"]), 1)
        self.assertEqual(self.state["videoLibrary"][0]["winningTrap"], 2)

    def test_add_video_updates_discovered_entry(self) -> None:
        self.add_file()
        server.sync_video_library(self.state)
        original_id = self.state["videoLibrary"][0]["id"]
        server.add_video(self.state, {
            "title": "First race", "source": "/videos/race01.mp4", "winningTrap": 2,
        })
        self.assertEqual(len(self.state["videoLibrary"]), 1)
        self.assertEqual(self.state["videoLibrary"][0]["id"], original_id)
        self.assertEqual(self.state["videoLibrary"][0]["winningTrap"], 2)

    def test_only_configured_available_files_can_be_drawn(self) -> None:
        ready = self.ready_video()
        self.add_file("race02.mp4")
        self.add_file("race03.mp4", b"version https://git-lfs.github.com/spec/v1\noid sha256:test\nsize 123\n")
        server.sync_video_library(self.state)
        self.state["videoLibrary"].append({
            "id": "missing", "title": "Missing", "source": "/videos/missing.mp4", "winningTrap": 3,
        })
        server.close_betting(self.state, {"raceNumber": 1})
        server.draw_video(self.state, {"raceNumber": 1})
        self.assertEqual(server.find_race(self.state)["selectedVideo"]["id"], ready["id"])

    def test_draw_avoids_repeating_ready_videos(self) -> None:
        self.ready_video()
        self.add_file("race02.mp4")
        server.sync_video_library(self.state)
        second = self.state["videoLibrary"][1]
        server.update_video(self.state, {"videoId": second["id"], "winningTrap": 2})
        for race in self.state["races"]:
            race["status"] = "closed"
            server.draw_video(self.state, {"raceNumber": race["raceNumber"]})
        ids = [race["selectedVideo"]["id"] for race in self.state["races"]]
        self.assertEqual(len(set(ids)), 2)

    def test_countdown_requires_ready_video(self) -> None:
        self.add_file()
        server.sync_video_library(self.state)
        with self.assertRaisesRegex(server.ApiError, "playable video"):
            server.start_countdown(self.state, {})
        self.assertIsNone(server.find_race(self.state)["bettingClosesAt"])

    def test_timer_closes_betting_if_video_becomes_unavailable(self) -> None:
        self.ready_video()
        server.add_player(self.state, {"name": "Alice"})
        player = self.state["players"][0]
        server.place_bet(self.state, {"playerId": player["id"], "trap": 1, "stake": 5})
        self.videos.joinpath("race01.mp4").unlink()
        race = server.find_race(self.state)
        race["bettingClosesAt"] = server.iso_from_timestamp(999)
        server.apply_race_timers(self.state, now_ts=1000)
        self.assertEqual(race["status"], "closed")
        self.assertIn("No race videos are ready", race["autoDrawError"])
        self.assertEqual(server.race_pool(race), 5)
        self.assertEqual(player["balance"], 20)

    def test_lfs_pointer_is_not_ready(self) -> None:
        video = self.ready_video()
        self.add_file(data=b"version https://git-lfs.github.com/spec/v1\noid sha256:test\nsize 123\n")
        self.assertIn("Git LFS", server.video_problem(video))

    def test_used_video_winner_is_locked(self) -> None:
        video = self.ready_video()
        server.close_betting(self.state, {})
        server.draw_video(self.state, {})
        with self.assertRaisesRegex(server.ApiError, "locked"):
            server.update_video(self.state, {"videoId": video["id"], "winningTrap": 1})
        self.assertEqual(server.find_race(self.state)["selectedVideo"]["winningTrap"], 4)

    def test_blank_demo_draw_can_be_recovered_without_changing_bets(self) -> None:
        ready = self.ready_video()
        server.add_player(self.state, {"name": "Alice"})
        player = self.state["players"][0]
        server.place_bet(self.state, {"playerId": player["id"], "trap": 1, "stake": 3})
        race = server.find_race(self.state)
        race["status"] = "video"
        race["selectedVideo"] = {"id": "video-01", "source": "", "winningTrap": 1}
        server.draw_video(self.state, {})
        self.assertEqual(race["selectedVideo"]["id"], ready["id"])
        self.assertEqual(server.race_pool(race), 3)
        self.assertEqual(player["balance"], 22)
        with self.assertRaisesRegex(server.ApiError, "Close betting"):
            server.draw_video(self.state, {})

    def test_failed_demo_recovery_keeps_original_selection(self) -> None:
        race = server.find_race(self.state)
        race["status"] = "video"
        original = {"id": "video-01", "source": "", "winningTrap": 1}
        race["selectedVideo"] = original.copy()
        with self.assertRaises(server.ApiError):
            server.draw_video(self.state, {})
        self.assertEqual(race["selectedVideo"], original)

    def test_blank_demo_cannot_settle_a_race(self) -> None:
        race = server.find_race(self.state)
        race["status"] = "video"
        race["selectedVideo"] = {"id": "video-01", "source": "", "winningTrap": 1}
        with self.assertRaisesRegex(server.ApiError, "playable race video"):
            server.record_result(self.state, {})
        self.assertIsNone(race["winningTrap"])

    def test_reset_keeps_video_configuration_and_removals(self) -> None:
        video = self.ready_video()
        self.add_file("race02.mp4")
        server.sync_video_library(self.state)
        removed = self.state["videoLibrary"][1]
        server.remove_video(self.state, {"videoId": removed["id"]})
        replacement = server.reset_event_preserving_videos(self.state, {"raceCount": 2})
        self.assertEqual(replacement["videoLibrary"], [video])
        self.assertIn(removed["source"], replacement["excludedVideoSources"])
        self.assertEqual(replacement["players"], [])

    def test_loading_persists_new_files_and_saved_winners(self) -> None:
        data_dir = self.root / "data"
        with patch.object(server, "DATA_DIR", data_dir), patch.object(server, "STATE_FILE", data_dir / "state.json"):
            server.save_state_unlocked(self.state)
            self.add_file()
            loaded = server.load_state_unlocked()
            video = loaded["videoLibrary"][0]
            server.update_video(loaded, {"videoId": video["id"], "winningTrap": 6})
            server.save_state_unlocked(loaded)
            self.assertEqual(server.load_state_unlocked()["videoLibrary"], [video])

    def test_unused_blank_placeholders_are_removed(self) -> None:
        self.state["videoLibrary"] = [{"id": "video-01", "source": "", "winningTrap": 1}]
        self.assertTrue(server.sync_video_library(self.state))
        self.assertEqual(self.state["videoLibrary"], [])

    def test_private_state_has_readiness_but_public_state_hides_catalog(self) -> None:
        self.add_file()
        server.sync_video_library(self.state)
        private = server.summarized_state(self.state, include_private=True)
        self.assertFalse(private["videoLibrary"][0]["ready"])
        self.assertEqual(private["videoLibrary"][0]["problem"], "Winning trap required")
        public = server.summarized_state(self.state)
        self.assertEqual(public["videoLibrary"], [])
        self.assertNotIn("excludedVideoSources", public)


class QuietHandler(server.RaceNightHandler):
    def log_message(self, format: str, *args) -> None:
        pass


class VideoServingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.root.joinpath("videos").mkdir()
        self.root.joinpath("videos", "race01.mp4").write_bytes(b"0123456789")
        self.static_patch = patch.object(server, "STATIC_DIR", self.root)
        self.static_patch.start()
        self.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        self.thread = threading.Thread(target=lambda: self.httpd.serve_forever(poll_interval=0.01), daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join()
        self.static_patch.stop()
        self.temporary.cleanup()

    def request(self, path: str = "/videos/race01.mp4", *, method: str = "GET", headers: dict | None = None):
        connection = http.client.HTTPConnection("127.0.0.1", self.httpd.server_port, timeout=3)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_full_video_streams_without_reading_entire_file_into_memory(self) -> None:
        with patch.object(Path, "read_bytes", side_effect=AssertionError("Whole-file read")):
            status, headers, body = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "video/mp4")
        self.assertEqual(headers["Accept-Ranges"], "bytes")
        self.assertEqual(body, b"0123456789")

    def test_partial_video_request(self) -> None:
        status, headers, body = self.request(headers={"Range": "bytes=2-5"})
        self.assertEqual(status, 206)
        self.assertEqual(headers["Content-Range"], "bytes 2-5/10")
        self.assertEqual(headers["Content-Length"], "4")
        self.assertEqual(body, b"2345")

    def test_suffix_and_open_ended_ranges(self) -> None:
        for value, expected in [("bytes=-3", b"789"), ("bytes=7-", b"789"), ("bytes=7-99", b"789")]:
            with self.subTest(value=value):
                status, _, body = self.request(headers={"Range": value})
                self.assertEqual(status, 206)
                self.assertEqual(body, expected)

    def test_unsatisfiable_or_malformed_ranges(self) -> None:
        for value in ["bytes=99-", "bytes=5-2", "bytes=-0", "bytes=-", "bytes=0-1,4-5", "bytes=" + "9" * 5000 + "-"]:
            with self.subTest(value=value[:30]):
                status, headers, body = self.request(headers={"Range": value})
                self.assertEqual(status, 416)
                self.assertEqual(headers["Content-Range"], "bytes */10")
                self.assertEqual(body, b"")

    def test_head_reports_video_length_without_body(self) -> None:
        status, headers, body = self.request(method="HEAD")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Length"], "10")
        self.assertEqual(body, b"")

    def test_encoded_filename_can_be_played(self) -> None:
        self.root.joinpath("videos", "Race 01.mp4").write_bytes(b"video")
        status, _, body = self.request("/videos/Race%2001.mp4")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"video")

    def test_missing_video_returns_not_found(self) -> None:
        self.assertEqual(self.request("/videos/missing.mp4")[0], 404)

    def test_lfs_pointer_returns_actionable_error(self) -> None:
        self.root.joinpath("videos", "race01.mp4").write_bytes(b"version https://git-lfs.github.com/spec/v1\n")
        status, _, body = self.request()
        self.assertEqual(status, 503)
        self.assertIn(b"Git LFS", body)

    def test_encoded_traversal_is_rejected(self) -> None:
        status, _, _ = self.request("/videos/%2e%2e/%2e%2e/private.mp4")
        self.assertEqual(status, 403)

    def test_browser_cancelling_a_video_download_is_handled(self) -> None:
        handler = QuietHandler.__new__(QuietHandler)
        handler.headers = {}
        handler.command = "GET"
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()
        handler.wfile.write.side_effect = ConnectionAbortedError("Browser closed the download")
        handler.serve_static("/videos/race01.mp4")
        handler.wfile.write.assert_called_once()


if __name__ == "__main__":
    unittest.main()
