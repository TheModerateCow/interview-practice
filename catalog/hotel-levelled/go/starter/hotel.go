package hotel

type Hotel struct{}

func NewHotel() *Hotel {
	panic("not implemented")
}

func (h *Hotel) AddRoom(day int, roomID string, roomType string, rate int) bool {
	panic("not implemented")
}

func (h *Hotel) Book(day int, guest string, roomID string, checkIn int, checkOut int) string {
	panic("not implemented")
}

func (h *Hotel) Cancel(day int, bookingID string) bool {
	panic("not implemented")
}

func (h *Hotel) Cost(day int, bookingID string) int {
	panic("not implemented")
}
