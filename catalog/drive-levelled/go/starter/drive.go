package drive

type Drive struct{}

func NewDrive() *Drive {
	panic("not implemented")
}

func (d *Drive) AddFile(path string, size int) bool {
	panic("not implemented")
}

func (d *Drive) GetFileSize(path string) int {
	panic("not implemented")
}

func (d *Drive) CopyFile(source string, dest string) bool {
	panic("not implemented")
}

func (d *Drive) DeleteFile(path string) int {
	panic("not implemented")
}
