"""Regression tests for citation forms that have tripped the detector or scorer."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from detect import detect
from score import cite_weights, norton_weights, sbn_weights


def kinds(text, tier=None):
    return [(c["kind"], c["tier"]) for c in detect(text) if tier is None or c["tier"] == tier]


def test_norton_and_paired_sbn_count_once():
    out = [c for c in detect("as Hume says (T 1.4.6.4; SBN 252).") if c["tier"] == "strict"]
    assert [c["kind"] for c in out] == ["norton"]


def test_slash_pairing():
    out = [c for c in detect("(T 1.4.6.2/SBN 251)") if c["tier"] == "strict"]
    assert len(out) == 1


def test_section_plus_sbn_page():
    assert ("section_plus_sbn", "strict") in kinds("identity. (T 1. iv. 6. 261) This")


def test_treatise_word_not_read_as_T():
    c = [c for c in detect("perceptions.\" (Treatise 252). On") if c["tier"] == "strict"][0]
    assert cite_weights(c["kind"], c["text"], c["value"])


def test_author_year_page():
    w = cite_weights("sbn_page", "(Hume 1978, p.252)", None)
    assert set(w) == {"1.4.6.2", "1.4.6.3", "1.4.6.4"}


def test_footnote_style_is_probable():
    assert ("footnote_page", "probable") in kinds("1 Hume, A Treatise of Human Nature, ed. Selby-Bigge (Oxford, 1978), p. 252.")


def test_bare_page_after_quote_is_probable():
    assert ("bare_page_after_quote", "probable") in kinds('"a bundle or collection of different perceptions" (252).')


def test_weights_sum_to_one():
    for w in (sbn_weights("253-63, 657-8"), norton_weights("1.4.6.5-22"), norton_weights("App.10")):
        assert abs(sum(w.values()) - 1) < 1e-9
