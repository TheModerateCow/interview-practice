from flags import FlagService


def _hidden_with_flags(*ids):
    """A service with the given flags created at time 1."""
    s = FlagService()
    for flag_id in ids:
        s.create_flag(1, flag_id)
    return s


# ---------------------------------------------------------------- level 1

def test_l1_create_and_default_off():
    s = FlagService()
    assert s.create_flag(1, "dark-mode") is True
    assert s.create_flag(2, "dark-mode") is False
    assert s.is_enabled(3, "dark-mode", "prod", "ana") is False
    assert s.is_enabled(4, "nope", "prod", "ana") is False


def test_l1_set_enabled_per_environment():
    s = _hidden_with_flags("dark-mode")
    assert s.set_enabled(2, "dark-mode", "prod", True) is True
    assert s.is_enabled(3, "dark-mode", "prod", "ana") is True
    assert s.is_enabled(4, "dark-mode", "prod", "bo") is True
    assert s.is_enabled(5, "dark-mode", "staging", "ana") is False
    assert s.set_enabled(6, "nope", "prod", True) is False
    assert s.set_enabled(7, "dark-mode", "prod", False) is True
    assert s.is_enabled(8, "dark-mode", "prod", "ana") is False
    assert s.set_enabled(9, "dark-mode", "prod", False) is True


def test_l1_targeting():
    s = _hidden_with_flags("dark-mode")
    assert s.add_target(2, "dark-mode", "staging", "ana") is True
    assert s.add_target(3, "dark-mode", "staging", "ana") is False
    assert s.is_enabled(4, "dark-mode", "staging", "ana") is True
    assert s.is_enabled(5, "dark-mode", "staging", "bo") is False
    assert s.is_enabled(6, "dark-mode", "prod", "ana") is False
    assert s.add_target(7, "nope", "staging", "ana") is False
    assert s.add_target(8, "dark-mode", "prod", "ana") is True


def test_l1_remove_target():
    s = _hidden_with_flags("dark-mode")
    s.add_target(2, "dark-mode", "prod", "ana")
    assert s.remove_target(3, "dark-mode", "prod", "ana") is True
    assert s.remove_target(4, "dark-mode", "prod", "ana") is False
    assert s.is_enabled(5, "dark-mode", "prod", "ana") is False
    assert s.remove_target(6, "dark-mode", "prod", "bo") is False
    assert s.remove_target(7, "dark-mode", "staging", "ana") is False
    assert s.remove_target(8, "nope", "prod", "ana") is False
    s.set_enabled(9, "dark-mode", "prod", True)
    s.add_target(10, "dark-mode", "prod", "cy")
    assert s.remove_target(11, "dark-mode", "prod", "cy") is True
    assert s.is_enabled(12, "dark-mode", "prod", "cy") is True  # on for everyone anyway


def test_l1_flags_independent():
    s = _hidden_with_flags("a", "b")
    s.set_enabled(3, "a", "prod", True)
    s.add_target(4, "b", "prod", "ana")
    assert s.is_enabled(5, "a", "prod", "bo") is True
    assert s.is_enabled(6, "b", "prod", "bo") is False
    assert s.is_enabled(7, "b", "prod", "ana") is True
    assert s.create_flag(8, "c") is True
    assert s.is_enabled(9, "c", "prod", "ana") is False


# ---------------------------------------------------------------- level 2
# buckets for "checkout": jo 1, eli 26, ana 36, gus 37, leo 42, bo 53, hal 71, cy 94, ivy 96

def test_l2_rollout_by_bucket():
    s = _hidden_with_flags("checkout")
    s.set_enabled(2, "checkout", "prod", True)
    assert s.set_rollout(3, "checkout", "prod", 40) is True
    assert s.is_enabled(4, "checkout", "prod", "ana") is True
    assert s.is_enabled(4, "checkout", "prod", "bo") is False
    assert s.is_enabled(4, "checkout", "prod", "leo") is False
    assert s.is_enabled(4, "checkout", "prod", "eli") is True
    assert s.set_rollout(5, "checkout", "prod", 0) is True
    assert s.is_enabled(6, "checkout", "prod", "ana") is False
    assert s.is_enabled(7, "checkout", "prod", "jo") is False
    assert s.set_rollout(8, "checkout", "prod", 100) is True
    assert s.is_enabled(9, "checkout", "prod", "cy") is True


def test_l2_rollout_boundary():
    s = _hidden_with_flags("checkout")
    s.set_enabled(2, "checkout", "prod", True)
    s.set_rollout(3, "checkout", "prod", 36)
    assert s.is_enabled(4, "checkout", "prod", "ana") is False
    assert s.is_enabled(5, "checkout", "prod", "eli") is True
    s.set_rollout(6, "checkout", "prod", 37)
    assert s.is_enabled(7, "checkout", "prod", "ana") is True
    assert s.is_enabled(8, "checkout", "prod", "gus") is False


def test_l2_rollout_rules():
    s = _hidden_with_flags("checkout")
    assert s.set_rollout(2, "checkout", "prod", -1) is False
    assert s.set_rollout(3, "checkout", "prod", 101) is False
    assert s.set_rollout(4, "checkout", "prod", 50.5) is False
    assert s.set_rollout(5, "nope", "prod", 50) is False
    assert s.set_rollout(6, "checkout", "prod", 90) is True
    assert s.is_enabled(7, "checkout", "prod", "ana") is False  # an off flag stays off
    s.set_enabled(8, "checkout", "prod", True)
    s.set_rollout(9, "checkout", "prod", 0)
    s.add_target(10, "checkout", "prod", "cy")
    assert s.is_enabled(11, "checkout", "prod", "cy") is True  # targets ignore the rollout
    assert s.is_enabled(12, "checkout", "prod", "ana") is False
    s.set_enabled(13, "checkout", "staging", True)
    assert s.is_enabled(14, "checkout", "staging", "ana") is True
    assert s.is_enabled(15, "checkout", "staging", "bo") is True


def test_l2_enabled_flags():
    s = _hidden_with_flags("search", "beta", "checkout", "dark-mode")
    s.set_enabled(2, "search", "prod", True)
    s.set_enabled(3, "checkout", "prod", True)
    s.set_rollout(4, "checkout", "prod", 40)
    s.add_target(5, "dark-mode", "prod", "bo")
    s.set_enabled(6, "beta", "staging", True)
    assert s.enabled_flags(7, "prod", "ana") == ["checkout", "search"]
    assert s.enabled_flags(8, "prod", "bo") == ["dark-mode", "search"]
    assert s.enabled_flags(9, "staging", "ana") == ["beta"]
    assert s.enabled_flags(10, "qa", "ana") == []


def test_l2_most_evaluated():
    s = _hidden_with_flags("search", "beta", "checkout", "dark-mode")
    t = 2
    for flag_id, n in [("search", 3), ("beta", 2), ("checkout", 2), ("dark-mode", 1)]:
        for i in range(n):
            s.is_enabled(t, flag_id, "prod", f"u{i}")
            t += 1
    s.is_enabled(t, "dark-mode", "staging", "ana")
    s.is_enabled(t + 1, "dark-mode", "staging", "ana")
    s.is_enabled(t + 2, "search", "staging", "ana")
    s.is_enabled(t + 3, "search", "staging", "bo")
    s.is_enabled(t + 4, "ghost", "prod", "ana")
    s.enabled_flags(t + 5, "prod", "ana")
    assert s.most_evaluated(t + 6, "prod", 10) == ["search(3)", "beta(2)", "checkout(2)", "dark-mode(1)"]
    assert s.most_evaluated(t + 7, "prod", 2) == ["search(3)", "beta(2)"]
    assert s.most_evaluated(t + 8, "staging", 5) == ["dark-mode(2)", "search(2)"]  # ties by id, not creation order
    assert s.most_evaluated(t + 9, "qa", 5) == []
    assert s.most_evaluated(t + 10, "prod", 0) == []


# ---------------------------------------------------------------- level 3

def test_l3_schedule_applies_at_its_time():
    s = _hidden_with_flags("launch")
    assert s.schedule_change(2, "launch", "prod", True, 10) == "s1"
    assert s.is_enabled(9, "launch", "prod", "ana") is False
    assert s.is_enabled(10, "launch", "prod", "ana") is True
    assert s.is_enabled(11, "launch", "staging", "ana") is False


def test_l3_schedule_ids_and_rejects():
    s = _hidden_with_flags("launch", "promo")
    assert s.schedule_change(3, "nope", "prod", True, 10) == ""
    assert s.schedule_change(4, "launch", "prod", True, 4) == ""
    assert s.schedule_change(5, "launch", "prod", True, 3) == ""
    assert s.schedule_change(6, "launch", "prod", True, 20) == "s1"
    assert s.schedule_change(7, "promo", "prod", True, 20) == "s2"
    assert s.schedule_change(8, "launch", "prod", False, 30) == "s3"


def test_l3_cancel():
    s = _hidden_with_flags("launch")
    s.schedule_change(2, "launch", "prod", True, 10)
    s.schedule_change(3, "launch", "prod", True, 20)
    assert s.cancel_schedule(4, "s1") is True
    assert s.cancel_schedule(5, "s1") is False
    assert s.cancel_schedule(6, "s9") is False
    assert s.is_enabled(12, "launch", "prod", "ana") is False
    assert s.cancel_schedule(20, "s2") is False  # already applied at its atTs
    assert s.is_enabled(21, "launch", "prod", "ana") is True
    assert s.schedule_change(22, "launch", "prod", False, 40) == "s3"


def test_l3_pending_order():
    s = _hidden_with_flags("launch", "promo")
    s.schedule_change(3, "launch", "prod", True, 50)
    s.schedule_change(4, "launch", "staging", True, 20)
    s.schedule_change(5, "promo", "prod", True, 30)
    s.schedule_change(6, "launch", "prod", False, 20)
    s.schedule_change(7, "launch", "qa", True, 40)
    assert s.pending(8, "launch") == ["s2", "s4", "s5", "s1"]
    assert s.pending(9, "promo") == ["s3"]
    assert s.pending(10, "nope") == []
    assert s.pending(20, "launch") == ["s5", "s1"]
    assert s.pending(35, "promo") == []


def test_l3_order_at_the_same_time():
    s = _hidden_with_flags("launch")
    s.schedule_change(2, "launch", "prod", False, 10)
    s.set_enabled(3, "launch", "prod", False)
    assert s.set_enabled(10, "launch", "prod", True) is True
    assert s.is_enabled(11, "launch", "prod", "ana") is True  # the call runs after the due change
    s.schedule_change(12, "launch", "prod", False, 20)
    s.schedule_change(13, "launch", "prod", True, 20)
    assert s.is_enabled(25, "launch", "prod", "ana") is True
    s.schedule_change(26, "launch", "prod", True, 30)
    s.schedule_change(27, "launch", "prod", False, 30)
    assert s.is_enabled(30, "launch", "prod", "ana") is False


# ---------------------------------------------------------------- level 4

def test_l4_history():
    s = _hidden_with_flags("search")
    s.set_enabled(2, "search", "prod", True)
    s.set_enabled(5, "search", "prod", False)
    s.set_enabled(9, "search", "prod", True)
    s.set_enabled(11, "search", "prod", True)
    s.set_enabled(12, "search", "staging", True)
    assert s.history(13, "search", "prod") == ["2:on", "5:off", "9:on", "11:on"]
    assert s.history(14, "search", "staging") == ["12:on"]
    assert s.history(15, "search", "qa") == []
    assert s.history(16, "nope", "prod") == []


def test_l4_history_scheduled_at_due_time():
    s = _hidden_with_flags("launch")
    s.set_enabled(2, "launch", "prod", False)
    s.schedule_change(3, "launch", "prod", True, 20)
    s.schedule_change(4, "launch", "prod", False, 25)
    s.cancel_schedule(5, "s2")
    s.set_enabled(30, "launch", "prod", False)
    assert s.history(31, "launch", "prod") == ["2:off", "20:on", "30:off"]


def test_l4_rollback_state():
    s = _hidden_with_flags("search")
    s.set_enabled(2, "search", "prod", True)
    s.set_enabled(5, "search", "prod", False)
    s.set_enabled(9, "search", "prod", True)
    assert s.rollback(12, "search", "prod", 5) is True
    assert s.is_enabled(13, "search", "prod", "ana") is False
    assert s.rollback(14, "search", "prod", 4) is True
    assert s.is_enabled(15, "search", "prod", "ana") is True
    assert s.rollback(16, "search", "prod", 1) is True
    assert s.is_enabled(17, "search", "prod", "ana") is False
    assert s.history(18, "search", "prod") == ["2:on", "5:off", "9:on", "12:off", "14:on", "16:off"]
    assert s.rollback(19, "search", "prod", 14) is True
    assert s.is_enabled(20, "search", "prod", "ana") is True


def test_l4_rollback_restores_rollout():
    s = _hidden_with_flags("checkout")
    s.set_enabled(2, "checkout", "prod", True)
    s.set_rollout(3, "checkout", "prod", 30)
    s.set_rollout(6, "checkout", "prod", 80)
    s.add_target(7, "checkout", "prod", "cy")
    assert s.rollback(8, "checkout", "prod", 4) is True
    assert s.is_enabled(9, "checkout", "prod", "eli") is True
    assert s.is_enabled(9, "checkout", "prod", "ana") is False
    assert s.is_enabled(9, "checkout", "prod", "hal") is False
    assert s.is_enabled(9, "checkout", "prod", "cy") is True  # targets are kept
    assert s.rollback(10, "checkout", "prod", 2) is True
    assert s.is_enabled(11, "checkout", "prod", "ana") is True
    assert s.is_enabled(11, "checkout", "prod", "hal") is True
    assert s.is_enabled(11, "checkout", "prod", "cy") is True
    assert s.rollback(12, "checkout", "prod", 6) is True
    assert s.is_enabled(13, "checkout", "prod", "hal") is True
    assert s.is_enabled(14, "checkout", "prod", "ivy") is False


def test_l4_rollback_rules():
    s = _hidden_with_flags("search")
    s.set_enabled(2, "search", "prod", True)
    s.set_enabled(3, "search", "staging", True)
    s.set_enabled(4, "search", "staging", False)
    assert s.rollback(5, "nope", "prod", 1) is False
    assert s.rollback(6, "search", "staging", 3) is True
    assert s.history(7, "search", "prod") == ["2:on"]
    assert s.history(8, "search", "staging") == ["3:on", "4:off", "6:on"]
    assert s.rollback(9, "search", "prod", 1) is True
    assert s.enabled_flags(10, "staging", "ana") == ["search"]
    assert s.enabled_flags(11, "prod", "ana") == []
