package helpdesk

type Desk struct{}

func NewDesk() *Desk {
	panic("not implemented")
}

func (d *Desk) AddAgent(ts int, agent string) bool {
	panic("not implemented")
}

func (d *Desk) OpenTicket(ts int, customer string, priority string) string {
	panic("not implemented")
}

func (d *Desk) Assign(ts int, ticketID string, agent string) bool {
	panic("not implemented")
}

func (d *Desk) SetStatus(ts int, ticketID string, status string) bool {
	panic("not implemented")
}

func (d *Desk) GetTicket(ts int, ticketID string) string {
	panic("not implemented")
}
