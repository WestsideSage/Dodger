from dodgeball_sim.engine_driver import (
    EngineDriver,
    DriverMatchInput,
    DriverMatchOutput,
)


def test_driver_input_holds_required_fields():
    inp = DriverMatchInput(
        match_id="m1",
        team_a_id="a",
        team_b_id="b",
        starters_a=("p1", "p2"),
        starters_b=("p3", "p4"),
        player_lookup={},
        policy_a=None,
        policy_b=None,
        seed=42,
    )
    assert inp.match_id == "m1"
    assert inp.seed == 42
    assert inp.starters_a == ("p1", "p2")
    assert inp.config == {}


def test_driver_output_defaults():
    out = DriverMatchOutput(
        events=(),
        winner_team_id=None,
        final_active_a=0,
        final_active_b=0,
    )
    assert out.moment_events == ()
    assert out.replay_state is None


def test_stub_driver_satisfies_protocol():
    class StubDriver:
        tier_id = "stub"

        def run(self, match_input: DriverMatchInput) -> DriverMatchOutput:
            return DriverMatchOutput(
                events=(),
                winner_team_id=match_input.team_a_id,
                final_active_a=1,
                final_active_b=0,
            )

    drv: EngineDriver = StubDriver()
    out = drv.run(
        DriverMatchInput(
            match_id="m",
            team_a_id="a",
            team_b_id="b",
            starters_a=(),
            starters_b=(),
            player_lookup={},
            policy_a=None,
            policy_b=None,
            seed=1,
        )
    )
    assert out.winner_team_id == "a"
