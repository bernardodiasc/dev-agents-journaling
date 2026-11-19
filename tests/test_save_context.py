import subprocess
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "src/skills/journaling/scripts"
sys.path.insert(0, str(SCRIPTS))
import save_context  # noqa: E402


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPTS / "save_context.py"), *args, "--stdout"],
                          capture_output=True, text=True, check=True).stdout


class SaveContextTest(unittest.TestCase):
    def test_note_is_saved_as_note_from_the_conversation(self):
        self.assertEqual(save_context.file_prefix("note"), "note")
        out = run("--kind", "note", "--note", "Drop the old export")
        self.assertIn("Source: Conversation (note)", out)
        self.assertNotIn("Jira", out)
        self.assertNotIn("Links:", out)

    def test_note_source_can_be_named(self):
        self.assertIn("Source: Slack (note)", run("--kind", "note", "--source", "slack", "--note", "x"))

    def test_ticket_stays_jira(self):
        self.assertEqual(save_context.file_prefix("ticket"), "jira")
        out = run("--kind", "ticket", "--url", "https://acme.atlassian.net/browse/PROJ-1")
        self.assertIn("Source: Jira (ticket)", out)

    def test_old_name_still_works(self):
        out = subprocess.run([sys.executable, str(SCRIPTS / "save_jira_context.py"), "--kind", "note",
                              "--note", "x", "--stdout"], capture_output=True, text=True, check=True).stdout
        self.assertIn("Source: Conversation (note)", out)


if __name__ == "__main__":
    unittest.main()
