from __future__ import annotations

from dodgeball_sim.copy_quality import has_unresolved_token, title_label


def test_has_unresolved_token_detects_raw_ids_and_template_blanks():
    assert has_unresolved_token("MVP: aurora_3")
    assert has_unresolved_token("Winner: {winner}")
    assert has_unresolved_token("Prospect: <name>")


def test_has_unresolved_token_allows_normal_sports_copy():
    assert not has_unresolved_token("MVP: Mara Voss")
    assert not has_unresolved_token("Aurora Sentinels Win The Final")


def test_title_label_normalizes_common_ui_labels():
    assert title_label("sim to next user match") == "Sim To Next User Match"
    assert title_label("mvp") == "MVP"
    assert title_label("hall of fame") == "Hall Of Fame"
