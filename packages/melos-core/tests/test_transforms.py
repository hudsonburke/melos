"""Tests for transform composition and quaternion operations."""

from melos.core.common.transforms import (
    compose_transforms,
    multiply_quaternions,
    quaternion_conjugate,
    rotate_vector,
)
from melos.core.common.types import Transform


def test_identity_composition():
    """Test that composing identity transforms yields identity."""
    identity = Transform(translation=(0.0, 0.0, 0.0), rotation=(1.0, 0.0, 0.0, 0.0))
    result = compose_transforms(identity, identity)
    
    assert result.translation == (0.0, 0.0, 0.0)
    assert result.rotation == (1.0, 0.0, 0.0, 0.0)


def test_translation_only_composition():
    """Test composing two translation-only transforms."""
    t1 = Transform(translation=(1.0, 2.0, 3.0), rotation=(1.0, 0.0, 0.0, 0.0))
    t2 = Transform(translation=(2.0, 3.0, 4.0), rotation=(1.0, 0.0, 0.0, 0.0))
    result = compose_transforms(t1, t2)
    
    assert result.translation == (3.0, 5.0, 7.0)
    assert result.rotation == (1.0, 0.0, 0.0, 0.0)


def test_quaternion_multiply_identity():
    """Test that multiplying a quaternion by identity yields the quaternion."""
    identity = (1.0, 0.0, 0.0, 0.0)
    q = (0.707, 0.707, 0.0, 0.0)
    result = multiply_quaternions(identity, q)
    
    assert result == q


def test_quaternion_conjugate_property():
    """Test that q * conj(q) approximately equals identity."""
    q = (0.707, 0.707, 0.0, 0.0)
    q_conj = quaternion_conjugate(q)
    result = multiply_quaternions(q, q_conj)
    
    # Should be approximately (1, 0, 0, 0)
    assert abs(result[0] - 1.0) < 1e-3
    assert abs(result[1]) < 1e-3
    assert abs(result[2]) < 1e-3
    assert abs(result[3]) < 1e-3


def test_rotate_vector_identity():
    """Test rotating a vector by identity quaternion."""
    identity = (1.0, 0.0, 0.0, 0.0)
    vector = (1.0, 2.0, 3.0)
    result = rotate_vector(identity, vector)
    
    assert abs(result[0] - 1.0) < 1e-6
    assert abs(result[1] - 2.0) < 1e-6
    assert abs(result[2] - 3.0) < 1e-6


def test_rotate_vector_180_around_z():
    """Test rotating a vector 180 degrees around the z-axis."""
    # 180 degree rotation around z-axis: (w, x, y, z) = (0, 0, 0, 1)
    rotation = (0.0, 0.0, 0.0, 1.0)
    vector = (1.0, 0.0, 0.0)
    result = rotate_vector(rotation, vector)
    
    # Should be approximately (-1, 0, 0)
    assert abs(result[0] + 1.0) < 1e-6
    assert abs(result[1]) < 1e-6
    assert abs(result[2]) < 1e-6


def test_compose_with_rotation_and_translation():
    """Test composing transforms with both rotation and translation."""
    # Parent: 90 degree rotation around z-axis + translation (1, 0, 0)
    parent = Transform(
        translation=(1.0, 0.0, 0.0),
        rotation=(0.707, 0.0, 0.0, 0.707)
    )
    # Child: translation (1, 0, 0)
    child = Transform(
        translation=(1.0, 0.0, 0.0),
        rotation=(1.0, 0.0, 0.0, 0.0)
    )
    result = compose_transforms(parent, child)
    
    # After rotating child's translation by parent's rotation, it should be (0, 1, 0)
    # So final translation should be (1, 1, 0)
    assert abs(result.translation[0] - 1.0) < 1e-3
    assert abs(result.translation[1] - 1.0) < 1e-3
    assert abs(result.translation[2] - 0.0) < 1e-3


def test_quaternion_conjugate_involution():
    """Test that conjugate of conjugate equals original."""
    q = (0.5, 0.5, 0.5, 0.5)
    q_conj = quaternion_conjugate(q)
    q_conj_conj = quaternion_conjugate(q_conj)
    
    assert q_conj_conj == q


def test_quaternion_multiply_associativity():
    """Test that quaternion multiplication is associative: (q1*q2)*q3 == q1*(q2*q3)."""
    q1 = (0.707, 0.707, 0.0, 0.0)
    q2 = (0.707, 0.0, 0.707, 0.0)
    q3 = (0.707, 0.0, 0.0, 0.707)
    lhs = multiply_quaternions(multiply_quaternions(q1, q2), q3)
    rhs = multiply_quaternions(q1, multiply_quaternions(q2, q3))
    for l, r in zip(lhs, rhs):
        assert abs(l - r) < 1e-6
