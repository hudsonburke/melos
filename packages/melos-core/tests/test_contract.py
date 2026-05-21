from melos.core.simulation import MUJOCO_BACKEND_CONTRACT


def test_mujoco_backend_contract_is_populated() -> None:
    assert MUJOCO_BACKEND_CONTRACT.backend == "mujoco"
    assert MUJOCO_BACKEND_CONTRACT.assumptions
    assert MUJOCO_BACKEND_CONTRACT.outputs
