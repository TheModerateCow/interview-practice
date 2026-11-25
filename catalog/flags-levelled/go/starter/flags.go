package flags

type FlagService struct{}

func NewFlagService() *FlagService {
	panic("not implemented")
}

func (f *FlagService) CreateFlag(ts int, flagID string) bool {
	panic("not implemented")
}

func (f *FlagService) SetEnabled(ts int, flagID string, env string, on bool) bool {
	panic("not implemented")
}

func (f *FlagService) AddTarget(ts int, flagID string, env string, userID string) bool {
	panic("not implemented")
}

func (f *FlagService) RemoveTarget(ts int, flagID string, env string, userID string) bool {
	panic("not implemented")
}

func (f *FlagService) IsEnabled(ts int, flagID string, env string, userID string) bool {
	panic("not implemented")
}
