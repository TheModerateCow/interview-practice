from hotel import Hotel


def _hidden_hotel():
    """Four rooms, added on day 1: two doubles, a single and a suite."""
    h = Hotel()
    assert h.add_room(1, "101", "double", 12000)
    assert h.add_room(1, "102", "double", 10000)
    assert h.add_room(1, "201", "single", 8000)
    assert h.add_room(1, "301", "suite", 30000)
    return h


# ---------------------------------------------------------------- level 1

def test_l1_add_room_rules():
    h = Hotel()
    assert h.add_room(1, "101", "double", 12000) is True
    assert h.add_room(2, "101", "suite", 30000) is False
    assert h.add_room(3, "102", "double", 0) is False
    assert h.add_room(4, "103", "double", -500) is False
    assert h.book(5, "maya", "102", 10, 12) == ""
    assert h.book(6, "maya", "101", 10, 12) == "b1"


def test_l1_ids_count_only_successful_bookings():
    h = _hidden_hotel()
    assert h.book(2, "maya", "101", 10, 13) == "b1"
    assert h.book(3, "leo", "999", 10, 13) == ""
    assert h.book(4, "leo", "102", 10, 13) == "b2"
    assert h.cost(5, "b1") == 36000
    assert h.cost(5, "b2") == 30000
    assert h.cost(6, "b3") == -1


def test_l1_book_rejects_bad_ranges():
    h = _hidden_hotel()
    assert h.book(2, "maya", "101", 10, 10) == ""
    assert h.book(2, "maya", "101", 12, 10) == ""
    assert h.book(2, "maya", "101", 10, 11) == "b1"
    assert h.cost(3, "b1") == 12000


def test_l1_overlaps_and_back_to_back():
    h = _hidden_hotel()
    assert h.book(2, "maya", "101", 10, 13) == "b1"
    assert h.book(2, "leo", "101", 13, 15) == "b2"
    assert h.book(2, "ana", "101", 8, 10) == "b3"
    assert h.book(2, "sam", "101", 9, 11) == ""
    assert h.book(2, "sam", "101", 12, 13) == ""
    assert h.book(2, "sam", "101", 5, 20) == ""
    assert h.book(2, "sam", "102", 10, 13) == "b4"


def test_l1_cancel_frees_nights():
    h = _hidden_hotel()
    assert h.book(2, "maya", "301", 10, 12) == "b1"
    assert h.cancel(3, "b1") is True
    assert h.cancel(4, "b1") is False
    assert h.cancel(4, "b9") is False
    assert h.cost(5, "b1") == -1
    assert h.book(6, "leo", "301", 11, 14) == "b2"
    assert h.cost(7, "b2") == 90000


# ---------------------------------------------------------------- level 2

def test_l2_available_sorted_by_rate_then_id():
    h = _hidden_hotel()
    assert h.add_room(1, "103", "double", 10000)
    assert h.add_room(1, "100", "double", 15000)
    assert h.available_rooms(2, "double", 10, 12) == ["102", "103", "101", "100"]
    assert h.available_rooms(2, "suite", 10, 12) == ["301"]


def test_l2_available_skips_booked_rooms():
    h = _hidden_hotel()
    h.book(2, "maya", "102", 10, 13)
    h.book(2, "leo", "101", 12, 14)
    assert h.available_rooms(3, "double", 10, 12) == ["101"]
    assert h.available_rooms(3, "double", 13, 15) == ["102"]
    assert h.available_rooms(3, "double", 11, 13) == []
    h.cancel(4, "b2")
    assert h.available_rooms(5, "double", 11, 13) == ["101"]


def test_l2_available_bad_queries():
    h = _hidden_hotel()
    assert h.available_rooms(2, "double", 12, 12) == []
    assert h.available_rooms(2, "double", 12, 10) == []
    assert h.available_rooms(2, "penthouse", 10, 12) == []
    assert Hotel().available_rooms(2, "double", 10, 12) == []


def test_l2_top_guests_ranking():
    h = _hidden_hotel()
    h.book(2, "maya", "101", 10, 12)
    h.book(2, "maya", "201", 20, 23)
    h.book(2, "leo", "102", 10, 15)
    h.book(2, "ana", "301", 10, 12)
    h.book(2, "bo", "301", 12, 14)
    assert h.top_guests(3, 10) == ["leo(5)", "maya(5)", "ana(2)", "bo(2)"]
    assert h.top_guests(3, 2) == ["leo(5)", "maya(5)"]
    h.cancel(4, "b2")
    assert h.top_guests(5, 3) == ["leo(5)", "ana(2)", "bo(2)"]


def test_l2_top_guests_empty():
    h = _hidden_hotel()
    assert h.top_guests(2, 3) == []
    h.book(3, "maya", "101", 10, 12)
    assert h.top_guests(4, 0) == []
    h.cancel(5, "b1")
    assert h.top_guests(6, 3) == []


# ---------------------------------------------------------------- level 3

def test_l3_no_booking_in_the_past():
    h = _hidden_hotel()
    assert h.book(10, "maya", "101", 9, 12) == ""
    assert h.available_rooms(10, "double", 9, 12) == []
    assert h.available_rooms(10, "double", 10, 12) == ["102", "101"]
    assert h.book(10, "maya", "101", 10, 12) == "b1"


def test_l3_check_in_only_on_arrival_day():
    h = _hidden_hotel()
    h.book(2, "maya", "101", 10, 12)
    assert h.check_in(9, "b1") is False
    assert h.check_in(10, "b9") is False
    assert h.check_in(10, "b1") is True
    assert h.check_in(10, "b1") is False
    assert h.cancel(10, "b1") is False


def test_l3_no_show_releases_the_room():
    h = _hidden_hotel()
    h.book(2, "maya", "101", 10, 13)
    h.book(2, "leo", "102", 10, 12)
    assert h.cost(10, "b1") == 36000
    assert h.available_rooms(10, "double", 10, 12) == []
    assert h.check_in(10, "b2") is True
    assert h.cost(11, "b1") == -1
    assert h.check_in(11, "b1") is False
    assert h.cancel(11, "b1") is False
    assert h.top_guests(11, 5) == ["leo(2)"]
    assert h.available_rooms(11, "double", 11, 13) == ["101"]
    assert h.book(11, "ana", "101", 11, 13) == "b3"


def test_l3_early_check_out_charges_nights_stayed():
    h = _hidden_hotel()
    h.book(2, "maya", "201", 10, 15)
    h.check_in(10, "b1")
    assert h.book(11, "leo", "201", 12, 14) == ""
    assert h.check_out(12, "b1") == 16000
    assert h.check_out(13, "b1") == -1
    assert h.cost(13, "b1") == 16000
    assert h.top_guests(13, 1) == ["maya(2)"]
    assert h.book(13, "leo", "201", 13, 15) == "b2"


def test_l3_check_out_edges():
    h = _hidden_hotel()
    h.book(2, "maya", "201", 10, 13)
    h.book(2, "leo", "301", 10, 12)
    h.book(2, "ana", "101", 10, 12)
    assert h.check_out(10, "b3") == -1
    h.check_in(10, "b1")
    h.check_in(10, "b2")
    assert h.check_out(10, "b1") == 8000
    assert h.check_out(20, "b2") == 60000
    assert h.check_out(20, "b9") == -1


# ---------------------------------------------------------------- level 4

def test_l4_bookings_keep_their_price():
    h = _hidden_hotel()
    assert h.book(2, "maya", "101", 10, 13) == "b1"
    assert h.set_rate(3, "101", 15000) is True
    assert h.cost(4, "b1") == 36000
    assert h.book(4, "leo", "101", 13, 15) == "b2"
    assert h.cost(5, "b2") == 30000


def test_l4_rate_history():
    h = Hotel()
    h.add_room(3, "101", "double", 100)
    h.set_rate(5, "101", 200)
    h.set_rate(9, "101", 300)
    assert h.rate_at(10, "101", 2) == -1
    assert h.rate_at(10, "101", 3) == 100
    assert h.rate_at(10, "101", 4) == 100
    assert h.rate_at(10, "101", 5) == 200
    assert h.rate_at(10, "101", 8) == 200
    assert h.rate_at(10, "101", 9) == 300
    assert h.rate_at(10, "101", 50) == 300
    assert h.rate_at(10, "999", 5) == -1


def test_l4_set_rate_rejects():
    h = _hidden_hotel()
    assert h.set_rate(2, "999", 5000) is False
    assert h.set_rate(2, "101", 0) is False
    assert h.set_rate(2, "101", -10) is False
    assert h.rate_at(3, "101", 2) == 12000
    assert h.rate_at(3, "999", 2) == -1


def test_l4_same_day_last_change_wins():
    h = _hidden_hotel()
    h.set_rate(5, "201", 9000)
    h.set_rate(5, "201", 9500)
    assert h.rate_at(6, "201", 5) == 9500
    assert h.rate_at(6, "201", 4) == 8000
    assert h.book(6, "maya", "201", 10, 12) == "b1"
    assert h.cost(7, "b1") == 19000


def test_l4_new_rates_reorder_and_check_out_uses_booked_price():
    h = _hidden_hotel()
    h.book(2, "maya", "101", 10, 14)
    assert h.set_rate(3, "102", 20000) is True
    assert h.set_rate(3, "101", 5000) is True
    assert h.available_rooms(4, "double", 20, 22) == ["101", "102"]
    h.check_in(10, "b1")
    assert h.check_out(12, "b1") == 24000
