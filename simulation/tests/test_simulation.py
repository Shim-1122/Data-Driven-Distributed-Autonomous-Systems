"""Smoke and invariant tests for the D3AS simulation engine and REST API."""
from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import simulation as sim  # noqa: E402
from app import app  # noqa: E402


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_algorithm_lists_have_expected_sizes():
    assert len(sim.VALID_ALGORITHMS) == 12
    assert len(sim.VALID_DEFENSE_ALGORITHMS) == 11
    assert len(set(sim.VALID_ALGORITHMS)) == 12
    assert len(set(sim.VALID_DEFENSE_ALGORITHMS)) == 11


@pytest.mark.parametrize("algorithm", sim.VALID_ALGORITHMS)
def test_every_attack_algorithm_runs_to_completion(algorithm):
    random.seed(7)
    state = sim.initialize_sim(algorithm=algorithm)
    sim.run_to_completion(state)
    public = sim.get_public_state(state)
    assert public["complete"] is True
    assert public["tick"] == sim.MAX_TICKS
    assert 0 <= public["drones_alive"] <= public["drones_total"]
    assert public["score"] >= 0


@pytest.mark.parametrize("defense", sim.VALID_DEFENSE_ALGORITHMS)
def test_every_defense_layout_generates_a_map(defense):
    random.seed(11)
    state = sim.initialize_sim(defense_algorithm=defense)
    pub = sim.get_public_state(state)
    entities = pub["entities"] if "entities" in pub else pub
    assert len(entities["radars"]) == sim.DEFAULT_NUM_RADARS
    assert len(entities["missile_launchers"]) == sim.DEFAULT_NUM_LAUNCHERS


def test_unrevealed_radars_hide_coordinates_at_tick_zero():
    random.seed(3)
    pub = sim.get_public_state(sim.initialize_sim())
    entities = pub["entities"] if "entities" in pub else pub
    for radar in entities["radars"]:
        assert not radar["revealed"]
        assert "x" not in radar and "y" not in radar


def test_score_never_exceeds_available_points():
    random.seed(5)
    state = sim.initialize_sim()
    sim.run_to_completion(state)
    pub = sim.get_public_state(state)
    ceiling = (
        sim.DEFAULT_NUM_RADARS * sim.RADAR_VALUE
        + sim.DEFAULT_NUM_GAS * sim.GAS_VALUE
        + sim.DEFAULT_NUM_LAUNCHERS * sim.MISSILE_VALUE
    )
    assert pub["score"] <= ceiling


def test_health_endpoint(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


def test_state_before_start_is_an_error(client):
    import app as app_module

    app_module._sim = None
    assert client.get("/api/state").status_code == 400


def test_start_tick_run_flow(client):
    r = client.post("/api/start", json={"algorithm": "meta_selector", "defense_algorithm": "honeycomb_grid"})
    assert r.status_code == 200
    assert r.get_json()["tick"] == 0

    r = client.post("/api/tick", json={"ticks": 5})
    assert r.status_code == 200
    assert r.get_json()["state"]["tick"] == 5

    r = client.post("/api/run")
    assert r.status_code == 200
    assert client.get("/api/state").get_json()["complete"] is True

    # ticking a finished sim is rejected
    assert client.post("/api/tick", json={}).status_code == 400


def test_unknown_algorithm_names_fall_back_to_defaults(client):
    r = client.post("/api/start", json={"algorithm": "nope", "defense_algorithm": "nope"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["algorithm"] == "grid_sweep"
    assert body["defense_algorithm"] == "random"
