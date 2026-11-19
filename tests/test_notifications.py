"""Tests for scripts/notifications.py (run: python3 -m unittest discover tests)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/skills/journaling/scripts"))
from notifications import html_url, notification_digest  # noqa: E402


def thread(reason, repo="acme/api", kind="pulls", num=12, title="Retry backoff"):
    return {
        "reason": reason,
        "unread": True,
        "repository": {"full_name": repo},
        "subject": {"title": title, "type": "PullRequest" if kind == "pulls" else "Issue",
                    "url": f"https://api.github.com/repos/{repo}/{kind}/{num}"},
    }


class HtmlUrlTest(unittest.TestCase):
    def test_pull_request_api_url_becomes_pull_page(self):
        self.assertEqual(html_url("https://api.github.com/repos/acme/api/pulls/12"),
                         "https://github.com/acme/api/pull/12")

    def test_issue_api_url_becomes_issue_page(self):
        self.assertEqual(html_url("https://api.github.com/repos/acme/docs/issues/41"),
                         "https://github.com/acme/docs/issues/41")

    def test_unknown_url_is_empty(self):
        self.assertEqual(html_url("https://evil.example/repos/acme/api/pulls/1"), "")
        self.assertEqual(html_url(None), "")


class DigestGroupingTest(unittest.TestCase):
    def test_review_request_is_on_me(self):
        d = notification_digest([thread("review_requested")], owners=["acme"], my_reviews={})
        self.assertEqual(d["watching"], [])
        [item] = d["on_me"]
        self.assertEqual(item["url"], "https://github.com/acme/api/pull/12")
        self.assertEqual(item["why"], "review requested")
        self.assertEqual(item["title"], "Retry backoff")

    def test_mention_assign_and_author_are_on_me(self):
        threads = [thread("mention", num=1), thread("assign", num=2), thread("author", num=3)]
        d = notification_digest(threads, owners=["acme"], my_reviews={})
        self.assertEqual([i["why"] for i in d["on_me"]], ["mentioned", "assigned", "activity on my thread"])

    def test_subscribed_activity_is_watching(self):
        d = notification_digest([thread("subscribed", kind="issues", num=41)], owners=["acme"], my_reviews={})
        self.assertEqual(d["on_me"], [])
        self.assertEqual(d["watching"][0]["url"], "https://github.com/acme/api/issues/41")


class OtherOrgTest(unittest.TestCase):
    def test_repo_outside_owners_is_flagged(self):
        d = notification_digest([thread("subscribed", repo="other-co/site"), thread("subscribed", repo="ACME/docs")],
                                owners=["acme"], my_reviews={})
        flags = {i["repo"]: i["other_org"] for i in d["watching"]}
        self.assertEqual(flags, {"other-co/site": True, "ACME/docs": False})

    def test_items_group_by_repo_with_other_orgs_last(self):
        threads = [thread("subscribed", repo="other-co/site"), thread("subscribed", repo="acme/web"),
                   thread("subscribed", repo="acme/api")]
        d = notification_digest(threads, owners=["acme"], my_reviews={})
        self.assertEqual([i["repo"] for i in d["watching"]], ["acme/api", "acme/web", "other-co/site"])

    def test_no_owners_flags_nothing(self):
        d = notification_digest([thread("subscribed", repo="other-co/site")], owners=[], my_reviews={})
        self.assertFalse(d["watching"][0]["other_org"])


class ReReviewTest(unittest.TestCase):
    URL = "https://github.com/acme/api/pull/12"

    def item(self, states, pending=True):
        reviews = {self.URL: {"states": states, "pending": pending}}
        d = notification_digest([thread("review_requested")], owners=["acme"], my_reviews=reviews)
        return (d["on_me"] + d["watching"])[0], bool(d["on_me"])

    def test_dismissed_review_then_new_request_is_re_review(self):
        item, on_me = self.item(["APPROVED", "DISMISSED"])
        self.assertEqual((item["why"], on_me), ("re-review (my review was dismissed)", True))

    def test_earlier_review_then_new_request_is_re_review(self):
        item, on_me = self.item(["COMMENTED", "CHANGES_REQUESTED"])
        self.assertEqual((item["why"], on_me), ("re-review", True))

    def test_no_earlier_review_is_first_review(self):
        item, on_me = self.item([])
        self.assertEqual((item["why"], on_me), ("review requested", True))

    def test_request_already_answered_moves_to_watching(self):
        # GitHub keeps reason=review_requested after the review is in.
        item, on_me = self.item(["CHANGES_REQUESTED", "DISMISSED", "APPROVED"], pending=False)
        self.assertEqual((item["why"], on_me), ("reviewed; new activity since", False))

    def test_request_withdrawn_without_review_moves_to_watching(self):
        item, on_me = self.item([], pending=False)
        self.assertEqual((item["why"], on_me), ("review request removed", False))

    def test_unknown_review_state_stays_review_requested(self):
        d = notification_digest([thread("review_requested")], owners=["acme"], my_reviews={})
        self.assertEqual(d["on_me"][0]["why"], "review requested")

if __name__ == "__main__":
    unittest.main()
