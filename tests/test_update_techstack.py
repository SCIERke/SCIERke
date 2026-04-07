import importlib.util
import pathlib
import unittest
from unittest.mock import patch


MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "update_techstack.py"
SPEC = importlib.util.spec_from_file_location("update_techstack", MODULE_PATH)
update_techstack = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(update_techstack)


class TestUpdateTechstack(unittest.TestCase):
    def test_to_badge_uses_mapped_logo_and_encodes_text(self):
        badge = update_techstack.to_badge("C++")
        self.assertIn("logo=cplusplus", badge)
        self.assertIn("badge/C%2B%2B-111827", badge)

    def test_build_techstack_block_empty(self):
        result = update_techstack.build_techstack_block({})
        self.assertEqual(result, "_No language data found yet._")

    def test_build_techstack_block_sorts_and_limits(self):
        langs = {f"Lang{i}": i for i in range(1, 12)}
        result = update_techstack.build_techstack_block(langs)
        self.assertEqual(result.count("img.shields.io/badge"), update_techstack.MAX_BADGES)
        self.assertIn("Lang11", result)
        self.assertNotIn("badge/Lang3-111827", result)

    def test_update_readme_replaces_marker_block(self):
        content = (
            "hello\n"
            f"{update_techstack.START_MARKER}\nold\n{update_techstack.END_MARKER}\n"
            "footer\n"
        )
        updated = update_techstack.update_readme(content, "NEW_BLOCK")
        self.assertIn(f"{update_techstack.START_MARKER}\nNEW_BLOCK\n{update_techstack.END_MARKER}", updated)
        self.assertNotIn("\nold\n", updated)

    def test_update_readme_raises_if_markers_missing(self):
        with self.assertRaises(ValueError):
            update_techstack.update_readme("no markers", "x")

    @patch.object(update_techstack, "get_json")
    def test_list_repos_handles_pagination(self, mock_get_json):
        mock_get_json.side_effect = [
            [{"name": "repo1"}],
            [{"name": "repo2"}],
            [],
        ]
        repos = update_techstack.list_repos("SCIERke", token="abc")
        self.assertEqual([r["name"] for r in repos], ["repo1", "repo2"])
        self.assertEqual(mock_get_json.call_count, 3)
        first_url = mock_get_json.call_args_list[0].args[0]
        second_url = mock_get_json.call_args_list[1].args[0]
        self.assertIn("page=1", first_url)
        self.assertIn("page=2", second_url)

    @patch.object(update_techstack, "get_json")
    def test_collect_languages_skips_fork_and_archived_and_sums(self, mock_get_json):
        repos = [
            {"fork": False, "archived": False, "languages_url": "https://a"},
            {"fork": True, "archived": False, "languages_url": "https://b"},
            {"fork": False, "archived": True, "languages_url": "https://c"},
            {"fork": False, "archived": False, "languages_url": "https://d"},
        ]
        mock_get_json.side_effect = [
            {"Python": 10, "TypeScript": 5, "Jupyter Notebook": 999},
            {"Python": 1, "C++": 9},
        ]
        totals = update_techstack.collect_languages(repos, token=None)
        self.assertEqual(dict(totals), {"Python": 11, "TypeScript": 5, "C++": 9})
        called_urls = [call.args[0] for call in mock_get_json.call_args_list]
        self.assertEqual(called_urls, ["https://a", "https://d"])


if __name__ == "__main__":
    unittest.main()
