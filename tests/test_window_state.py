import unittest

from ankiforge_ai.workbench.window_state import WorkbenchWindowState


class WorkbenchWindowStateTests(unittest.TestCase):
    def test_round_trip_accepts_bounded_canonical_base64_geometry(self):
        state = WorkbenchWindowState(
            geometry="AQIDBA==",
            maximized=True,
        )

        self.assertEqual(
            WorkbenchWindowState.from_mapping(state.to_safe_dict()),
            state,
        )
        self.assertEqual(
            state.to_safe_dict(),
            {"geometry": "AQIDBA==", "maximized": True},
        )

    def test_empty_geometry_is_a_safe_default(self):
        self.assertEqual(
            WorkbenchWindowState.defaults(),
            WorkbenchWindowState(geometry="", maximized=False),
        )

    def test_unknown_or_missing_fields_are_rejected(self):
        for value in (
            {"geometry": "AQIDBA=="},
            {"maximized": False},
            {
                "geometry": "AQIDBA==",
                "maximized": False,
                "api_key": "not-allowed",
            },
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    WorkbenchWindowState.from_mapping(value)

    def test_non_boolean_maximized_value_is_rejected(self):
        for value in (0, 1, "false", None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    WorkbenchWindowState(
                        geometry="AQIDBA==",
                        maximized=value,
                    )

    def test_malformed_noncanonical_and_oversized_geometry_are_rejected(self):
        for value in (
            "not base64",
            "AQIDBA",
            "A" * 8193,
        ):
            with self.subTest(value=value[:20]):
                with self.assertRaises(ValueError):
                    WorkbenchWindowState(
                        geometry=value,
                        maximized=False,
                    )

    def test_secret_shaped_decoded_geometry_is_rejected(self):
        with self.assertRaises(ValueError):
            WorkbenchWindowState(
                geometry=(
                    "c2stYWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXo="
                ),
                maximized=False,
            )

    def test_repr_never_contains_geometry_payload(self):
        state = WorkbenchWindowState(
            geometry="AQIDBA==",
            maximized=True,
        )

        self.assertNotIn("AQIDBA==", repr(state))


if __name__ == "__main__":
    unittest.main()
