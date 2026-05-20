from dodgeball_sim.rulesets import BallMaterial
from dodgeball_sim.sequence import (
    SequenceContact,
    SequenceContactKind,
    SequenceLedger,
    SequenceOfPlay,
    resolve_sequence,
    resolve_simultaneous_catches,
    sequence_event,
)


def _seq(material=BallMaterial.FOAM, valid=True, clock_expired=False):
    return SequenceOfPlay(
        sequence_id="s1",
        match_id="m1",
        game_id="g1",
        thrower_id="tA",
        thrower_team_id="A",
        ball_id="b1",
        release_time_ms=0,
        release_valid=valid,
        material=material,
        clock_expired_at_release=clock_expired,
    )


def test_hit_not_final_until_resolution():
    seq = _seq()
    seq.add_pending_out("vB", "hit")
    # before resolve, ledger has pending only
    assert seq.final is None
    resolve_sequence(seq)
    assert "vB" in seq.final.outs
    assert seq.final.thrower_out is False


def test_foam_ricochet_catch_saves_hit_player():
    seq = _seq(material=BallMaterial.FOAM)
    seq.add_pending_out("vB", "hit_then_ricochet")
    seq.add_pending_save("vB", "ricochet_catch")
    seq.add_catch("cA", timestamp_ms=10)
    ruling = resolve_sequence(seq)
    assert "vB" in ruling.saves
    assert "tA" in ruling.outs  # thrower out from catch
    assert ruling.thrower_out is True
    # Section 21 (block/ricochet) and 22 (catch) referenced.
    labels = tuple(r.as_label() for r in ruling.rule_refs)
    assert "21" in labels and "22" in labels


def test_cloth_ricochet_catch_does_not_save_hit_player():
    seq = _seq(material=BallMaterial.CLOTH)
    seq.add_pending_out("vB", "hit_then_ricochet")
    seq.add_pending_save("vB", "ricochet_catch")
    seq.add_catch("cA", timestamp_ms=10)
    ruling = resolve_sequence(seq)
    assert "tA" in ruling.outs  # thrower out from catch
    assert "vB" in ruling.outs  # cloth: still out
    assert "vB" not in ruling.saves


def test_catch_after_clock_expiry_still_eliminates_thrower():
    seq = _seq(clock_expired=True)
    seq.add_catch("cA", timestamp_ms=20)
    ruling = resolve_sequence(seq)
    assert ruling.thrower_out is True
    assert "tA" in ruling.outs
    labels = tuple(r.as_label() for r in ruling.rule_refs)
    assert "14" in labels


def test_clock_expired_no_catch_outs_thrower():
    seq = _seq(clock_expired=True)
    ruling = resolve_sequence(seq)
    assert ruling.thrower_out is True
    assert "tA" in ruling.outs


def test_invalid_release_outs_thrower_section_25():
    seq = _seq(valid=False)
    seq.add_pending_out("vB", "hit")
    ruling = resolve_sequence(seq)
    assert "tA" in ruling.outs
    # the hit player is not out -- ball was never live
    assert "vB" not in ruling.outs
    labels = tuple(r.as_label() for r in ruling.rule_refs)
    assert "25" in labels


def test_second_ball_out_cannot_be_saved_later():
    # Ledger handles cross-sequence finality
    ledger = SequenceLedger()
    seq1 = _seq(material=BallMaterial.FOAM)
    seq1.sequence_id = "s1"
    seq1.ball_id = "b1"
    seq1.add_pending_out("vB", "hit")
    seq1.add_pending_save("vB", "ricochet_catch")
    seq1.add_catch("cA", timestamp_ms=50)
    ledger.open_sequence(seq1)
    # Meanwhile a second ball already made vB out before s1 closes
    ledger.apply_second_ball_out("vB")
    ruling = ledger.close_sequence("s1")
    assert "vB" not in ruling.saves
    # vB stays confirmed out
    assert "vB" in ledger.confirmed_outs


def test_simultaneous_catches_resolved_deterministically():
    seq = _seq()
    seq.add_catch("cB", timestamp_ms=10)
    seq.add_catch("cA", timestamp_ms=10)
    seq.add_catch("cC", timestamp_ms=20)
    sims = resolve_simultaneous_catches(seq)
    # Same timestamp -> sorted by catcher_id
    assert tuple(c.catcher_id for c in sims) == ("cA", "cB")


def test_sequence_event_payload_includes_outs_and_saves():
    seq = _seq()
    seq.add_pending_out("vB", "hit")
    resolve_sequence(seq)
    ev = sequence_event(seq)
    assert ev.payload["outs"] == ["vB"]
    assert ev.payload["thrower_out"] is False
    assert ev.sequence_id == "s1"
