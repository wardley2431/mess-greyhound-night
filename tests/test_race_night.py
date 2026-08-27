from __future__ import annotations

import unittest

import server


class RaceNightRulesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = server.new_event_state(seed=42)
        server.add_player(self.state, {"name": "Alice"})
        server.add_player(self.state, {"name": "Bob"})
        self.alice = self.state["players"][0]
        self.bob = self.state["players"][1]

    def test_lineups_have_six_unique_dogs_per_race(self) -> None:
        self.assertEqual(len(self.state["races"]), 10)
        for race in self.state["races"]:
            self.assertEqual([entry["trap"] for entry in race["lineup"]], [1, 2, 3, 4, 5, 6])
            dog_ids = [entry["dogId"] for entry in race["lineup"]]
            self.assertEqual(len(dog_ids), len(set(dog_ids)))

    def test_players_get_pins_and_public_state_redacts_them(self) -> None:
        self.assertRegex(self.alice["pin"], r"^\d{4}$")
        private = server.summarized_state(self.state, include_private=True)
        public = server.summarized_state(self.state)
        self.assertIn("pin", private["players"][0])
        self.assertNotIn("pin", public["players"][0])

    def test_bets_deduct_balance_and_close_blocks_new_bets(self) -> None:
        server.place_bet(self.state, {"playerId": self.alice["id"], "trap": 3, "stake": 4})
        self.assertEqual(self.alice["balance"], 21)
        server.close_betting(self.state, {"raceNumber": 1})
        with self.assertRaisesRegex(server.ApiError, "Betting is closed"):
            server.place_bet(self.state, {"playerId": self.bob["id"], "trap": 3, "stake": 1})

    def test_punter_betting_requires_reference_and_pin(self) -> None:
        with self.assertRaisesRegex(server.ApiError, "incorrect"):
            server.place_punter_bet(
                self.state,
                {"reference": self.alice["reference"], "pin": "0000", "trap": 1, "stake": 3},
            )

        server.place_punter_bet(
            self.state,
            {"reference": self.alice["reference"], "pin": self.alice["pin"], "trap": 1, "stake": 3},
        )
        self.assertEqual(self.alice["balance"], 22)
        self.assertEqual(server.find_race(self.state, 1)["bets"][0]["playerId"], self.alice["id"])

    def test_role_login_accepts_admin_or_punter(self) -> None:
        admin = server.authenticate_login(
            self.state,
            {"reference": server.ADMIN_REFERENCE, "pin": server.ADMIN_PIN},
        )
        punter = server.authenticate_login(
            self.state,
            {"reference": self.alice["reference"], "pin": self.alice["pin"]},
        )

        self.assertEqual(admin["role"], "admin")
        self.assertEqual(punter["role"], "punter")
        self.assertEqual(punter["punter"]["player"]["name"], "Alice")

    def test_race_stake_limit_applies_across_dogs(self) -> None:
        self.state["event"]["maxRaceStake"] = 8
        server.place_bet(self.state, {"playerId": self.alice["id"], "trap": 1, "stake": 5})
        server.place_bet(self.state, {"playerId": self.alice["id"], "trap": 2, "stake": 3})

        with self.assertRaisesRegex(server.ApiError, "Race limit"):
            server.place_bet(self.state, {"playerId": self.alice["id"], "trap": 3, "stake": 1})

        self.assertEqual(self.alice["balance"], 17)
        self.assertEqual(server.race_stake_for_player(server.find_race(self.state, 1), self.alice["id"]), 8)

    def test_tote_payouts_distribute_the_whole_pool(self) -> None:
        race = server.find_race(self.state, 1)
        server.place_bet(self.state, {"playerId": self.alice["id"], "trap": 1, "stake": 5})
        server.place_bet(self.state, {"playerId": self.alice["id"], "trap": 2, "stake": 5})
        server.place_bet(self.state, {"playerId": self.bob["id"], "trap": 1, "stake": 10})
        server.close_betting(self.state, {"raceNumber": 1})
        race["status"] = "video"
        race["selectedVideo"] = {"id": "video-test", "title": "Test Video", "source": "", "winningTrap": 1}
        server.record_result(self.state, {"raceNumber": 1, "winningTrap": 1})

        self.assertEqual(server.race_pool(race), 20)
        self.assertEqual(sum(payout["amount"] for payout in race["payouts"]), 20)
        self.assertEqual(race["unclaimedPool"], 0)
        self.assertEqual([self.alice["balance"], self.bob["balance"]], [22, 28])

    def test_video_draw_requires_closed_betting(self) -> None:
        with self.assertRaisesRegex(server.ApiError, "Close betting"):
            server.draw_video(self.state, {"raceNumber": 1})
        server.close_betting(self.state, {"raceNumber": 1})
        with self.assertRaisesRegex(server.ApiError, "Draw a race video"):
            server.record_result(self.state, {"raceNumber": 1, "winningTrap": 1})
        server.draw_video(self.state, {"raceNumber": 1})
        race = server.find_race(self.state, 1)
        self.assertEqual(race["status"], "video")
        self.assertIsNotNone(race["selectedVideo"])

        private = server.summarized_state(self.state, include_private=True)
        public = server.summarized_state(self.state)
        self.assertIn("winningTrap", private["currentRace"]["selectedVideo"])
        self.assertNotIn("winningTrap", public["currentRace"]["selectedVideo"])

    def test_open_race_waits_for_admin_countdown(self) -> None:
        race = server.find_race(self.state, 1)

        changed = server.apply_race_timers(self.state, now_ts=1000)

        self.assertFalse(changed)
        self.assertEqual(race["status"], "open")
        self.assertIsNone(race["bettingClosesAt"])

    def test_admin_can_start_countdown_for_open_race(self) -> None:
        race = server.find_race(self.state, 1)

        server.start_countdown(self.state, {"raceNumber": 1})

        self.assertEqual(race["status"], "open")
        self.assertIsNotNone(race["bettingClosesAt"])
        with self.assertRaisesRegex(server.ApiError, "already running"):
            server.start_countdown(self.state, {"raceNumber": 1})

    def test_timer_auto_closes_betting_and_draws_video(self) -> None:
        race = server.find_race(self.state, 1)
        race["bettingClosesAt"] = server.iso_from_timestamp(999)

        changed = server.apply_race_timers(self.state, now_ts=1000)

        self.assertTrue(changed)
        self.assertEqual(race["status"], "video")
        self.assertIsNotNone(race["selectedVideo"])
        self.assertEqual(race["closedAt"], server.iso_from_timestamp(1000))
        self.assertIsNone(race["bettingClosesAt"])

    def test_result_must_match_selected_video(self) -> None:
        race = server.find_race(self.state, 1)
        server.close_betting(self.state, {"raceNumber": 1})
        race["status"] = "video"
        race["selectedVideo"] = {"id": "video-test", "title": "Test Video", "source": "", "winningTrap": 5}
        with self.assertRaisesRegex(server.ApiError, "must match"):
            server.record_result(self.state, {"raceNumber": 1, "winningTrap": 2})

    def test_advance_opens_the_next_race_after_result(self) -> None:
        race = server.find_race(self.state, 1)
        server.close_betting(self.state, {"raceNumber": 1})
        race["status"] = "video"
        race["selectedVideo"] = {"id": "video-test", "title": "Test Video", "source": "", "winningTrap": 4}
        server.record_result(self.state, {"raceNumber": 1, "winningTrap": 4})
        server.advance_race(self.state, {"raceNumber": 1})
        self.assertEqual(self.state["event"]["currentRaceNumber"], 2)
        self.assertEqual(server.find_race(self.state, 2)["status"], "open")
        self.assertIsNone(server.find_race(self.state, 2)["bettingClosesAt"])


if __name__ == "__main__":
    unittest.main()
