"""R22.3: parse Link relationship parameters, never raw text of URLs or title.

Transport tests use GitHubReadOnly.get_json with a fake HTTP opener. No network,
secrets or authority. Distinguish malformed Link from actual pagination.
"""
from email.message import Message
from unittest.mock import Mock

import pytest
import ario_repo_self_audit as mod

URL = mod.API + "/commits/" + "c" * 40 + "/check-runs?per_page=100"
BODY = b'{"total_count":1,"check_runs":[{}]}'


def fetch_with_links(*values):
    headers = Message()
    headers.add_header("Content-Length", str(len(BODY)))
    for value in values:
        headers.add_header("Link", value)

    class Response:
        status = 200

        def __init__(self):
            self.headers = headers

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, cap):
            return BODY

    reader = mod.GitHubReadOnly()
    reader.opener = Mock()
    reader.opener.open.return_value = Response()
    return reader.get_json(URL)


@pytest.mark.parametrize("header", [
    '<https://api.github.com/runs?rel=next&page=1>; rel="last"',
    '<https://api.github.com/runs>; title="rel=next"; rel="last"',
    '<https://api.github.com/runs>; rel="next-foo"',
    '<https://api.github.com/runs>; rel="not-next"',
    '<https://api.github.com/runs?a=1,2;b=3>; title="one, two; rel=next"; rel=last',
    '<https://api.github.com/runs>; title="escaped \"rel=next\""; rel="first"',
    '<https://api.github.com/runs>; rel="prev", <https://api.github.com/runs?page=7>; rel="last"',
])
def test_valid_non_next_link_is_not_mistaken_for_next(header):
    assert fetch_with_links(header)["total_count"] == 1


@pytest.mark.parametrize("header", [
    '<https://api.github.com/runs?page=2>; rel="next"',
    '<https://api.github.com/runs?page=2>; rel=next',
    '<https://api.github.com/runs?page=2>; rel="prev next"',
    '<https://api.github.com/runs?page=2>; rel="NEXT"',
    '<https://api.github.com/runs>; rel=last, <https://api.github.com/runs?page=2>; rel="next"',
])
def test_actual_next_relation_is_always_fail_closed(header):
    with pytest.raises(mod.ReadUnknown, match="PAGINATION_NEXT_LINK_PRESENT"):
        fetch_with_links(header)


def test_next_only_in_second_link_header_is_fail_closed():
    with pytest.raises(mod.ReadUnknown, match="PAGINATION_NEXT_LINK_PRESENT"):
        fetch_with_links(
            '<https://api.github.com/runs?page=1>; rel="first"',
            '<https://api.github.com/runs?page=2>; rel="next"',
        )


@pytest.mark.parametrize("header", [
    '<https://api.github.com/runs?rel=next>',  # rel parameter is REQUIRED
    '<https://api.github.com/runs>; rel=next; rel=last',
    '<https://api.github.com/runs>; rel=last; rel=next',
    '<https://api.github.com/runs>; rel="next',
    '<https://api.github.com/runs>; rel=',
    '   ',
    '<https://api.github.com/runs>; rel="last",',
    '<https://api.github.com/runs>; title="unterminated; rel=next',
    '<https://api.github.com/runs>; rel="last,next"',
    '<https://api.github.com/runs>; rel="first"; title="x"garbage',
])
def test_malformed_or_ambiguous_link_is_unknown(header):
    with pytest.raises(mod.ReadUnknown, match="PAGINATION_LINK_INVALID"):
        fetch_with_links(header)


def test_bounded_link_header_count_is_fail_closed():
    with pytest.raises(mod.ReadUnknown, match="PAGINATION_LINK_INVALID"):
        fetch_with_links(*(['<https://api.github.com/runs>; rel="last"'] * 9))


def test_large_link_header_is_fail_closed():
    with pytest.raises(mod.ReadUnknown, match="PAGINATION_LINK_INVALID"):
        fetch_with_links('<https://api.github.com/runs?' + 'a' * 8192 + '>; rel=last')


def test_no_link_is_not_proof_of_permanent_freshness():
    assert fetch_with_links()["total_count"] == 1
