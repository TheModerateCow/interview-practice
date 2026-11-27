package slo

type SloMonitor struct{}

func NewSloMonitor() *SloMonitor {
	panic("not implemented")
}

func (s *SloMonitor) AddService(service string) bool {
	panic("not implemented")
}

func (s *SloMonitor) Ingest(service string, firstMinute int, requests []int, errors []int) bool {
	panic("not implemented")
}

func (s *SloMonitor) ErrorRate(service string, start int, end int) (int, bool) {
	panic("not implemented")
}

func (s *SloMonitor) LatestMinute(service string) (int, bool) {
	panic("not implemented")
}
