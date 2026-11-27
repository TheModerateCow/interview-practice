package rental

type RentalDesk struct{}

func NewRentalDesk() *RentalDesk {
	panic("not implemented")
}

func (d *RentalDesk) AddCar(ts int, carID string, carClass string, branch string) bool {
	panic("not implemented")
}

func (d *RentalDesk) Rent(ts int, customer string, branch string, carClass string, days int) string {
	panic("not implemented")
}

func (d *RentalDesk) ReturnCar(ts int, carID string) bool {
	panic("not implemented")
}

func (d *RentalDesk) Status(ts int, carID string) string {
	panic("not implemented")
}
