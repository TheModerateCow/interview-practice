package restaurant

type Restaurant struct{}

func NewRestaurant() *Restaurant {
	panic("not implemented")
}

func (r *Restaurant) AddTable(ts int, tableID string, seats int) bool {
	panic("not implemented")
}

func (r *Restaurant) Book(ts int, name string, size int, slot int) string {
	panic("not implemented")
}

func (r *Restaurant) Cancel(ts int, reservationID string) bool {
	panic("not implemented")
}

func (r *Restaurant) TableOf(ts int, reservationID string) string {
	panic("not implemented")
}

func (r *Restaurant) PartyAt(ts int, tableID string, slot int) string {
	panic("not implemented")
}
