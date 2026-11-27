// Package drive is cloud file storage: files by path, folder listings, users with storage quotas, file versions and a trash.
package drive

import (
	"fmt"
	"sort"
	"strings"
)

type user struct{ capacity, used int }

type file struct {
	owner    *user // nil: nobody's, counts against no quota
	versions []int // sizes, last = current
}

type trashed struct {
	path string
	f    *file
}

type Drive struct {
	files map[string]*file
	users map[string]*user
	trash []trashed // in deletion order
}

func NewDrive() *Drive {
	return &Drive{files: map[string]*file{}, users: map[string]*user{}}
}

func sum(xs []int) int {
	t := 0
	for _, x := range xs {
		t += x
	}
	return t
}

func (f *file) size() int { return f.versions[len(f.versions)-1] }

// charge counts size against u's quota; false, changing nothing, if it doesn't fit.
func charge(u *user, size int) bool {
	if u == nil {
		return true
	}
	if u.used+size > u.capacity {
		return false
	}
	u.used += size
	return true
}

func free(u *user, size int) {
	if u != nil {
		u.used -= size
	}
}

func (d *Drive) add(owner *user, path string, size int) bool {
	if _, ok := d.files[path]; ok || size < 0 || !charge(owner, size) {
		return false
	}
	d.files[path] = &file{owner: owner, versions: []int{size}}
	return true
}

func (d *Drive) copy(owner *user, source, dest string) bool {
	src, ok := d.files[source]
	if !ok {
		return false
	}
	if _, taken := d.files[dest]; taken {
		return false
	}
	return d.add(owner, dest, src.size())
}

// ---------------------------------------------------------------- level 1

func (d *Drive) AddFile(path string, size int) bool {
	return d.add(nil, path, size)
}

func (d *Drive) GetFileSize(path string) int {
	f, ok := d.files[path]
	if !ok {
		return -1
	}
	return f.size()
}

func (d *Drive) CopyFile(source string, dest string) bool {
	src, ok := d.files[source]
	return ok && d.copy(src.owner, source, dest)
}

func (d *Drive) DeleteFile(path string) int {
	f, ok := d.files[path]
	if !ok {
		return -1
	}
	delete(d.files, path)
	free(f.owner, sum(f.versions))
	d.trash = append(d.trash, trashed{path, f})
	return f.size()
}

// ---------------------------------------------------------------- level 2

type entry struct {
	path string
	size int
}

func (d *Drive) under(prefix string) []entry {
	var out []entry
	for p, f := range d.files {
		if strings.HasPrefix(p, prefix) {
			out = append(out, entry{p, f.size()})
		}
	}
	return out
}

func (d *Drive) LargestFiles(prefix string, n int) []string {
	es := d.under(prefix)
	sort.Slice(es, func(i, j int) bool {
		if es[i].size != es[j].size {
			return es[i].size > es[j].size
		}
		return es[i].path < es[j].path
	})
	out := []string{}
	for i := 0; i < len(es) && i < n; i++ {
		out = append(out, fmt.Sprintf("%s(%d)", es[i].path, es[i].size))
	}
	return out
}

func (d *Drive) FolderSize(prefix string) int {
	t := 0
	for _, e := range d.under(prefix) {
		t += e.size
	}
	return t
}

// ---------------------------------------------------------------- level 3

func (d *Drive) AddUser(userID string, capacity int) bool {
	if _, ok := d.users[userID]; ok || capacity <= 0 {
		return false
	}
	d.users[userID] = &user{capacity: capacity}
	return true
}

func (d *Drive) AddFileBy(userID string, path string, size int) int {
	u, ok := d.users[userID]
	if !ok || !d.add(u, path, size) {
		return -1
	}
	return u.capacity - u.used
}

func (d *Drive) CopyFileBy(userID string, source string, dest string) int {
	u, ok := d.users[userID]
	if !ok || !d.copy(u, source, dest) {
		return -1
	}
	return u.capacity - u.used
}

func (d *Drive) Remaining(userID string) int {
	u, ok := d.users[userID]
	if !ok {
		return -1
	}
	return u.capacity - u.used
}

// ---------------------------------------------------------------- level 4

func (d *Drive) OverwriteFile(path string, size int) int {
	f, ok := d.files[path]
	if !ok || size < 0 || !charge(f.owner, size) {
		return -1
	}
	f.versions = append(f.versions, size)
	return len(f.versions)
}

func (d *Drive) RestoreVersion(path string, version int) int {
	f, ok := d.files[path]
	if !ok || version < 1 || version > len(f.versions) {
		return -1
	}
	free(f.owner, sum(f.versions[version:]))
	f.versions = f.versions[:version]
	return f.size()
}

func (d *Drive) RestoreFile(path string) bool {
	if _, ok := d.files[path]; ok {
		return false
	}
	for i := len(d.trash) - 1; i >= 0; i-- {
		t := d.trash[i]
		if t.path == path {
			if !charge(t.f.owner, sum(t.f.versions)) {
				return false
			}
			d.trash = append(d.trash[:i], d.trash[i+1:]...)
			d.files[path] = t.f
			return true
		}
	}
	return false
}

func (d *Drive) EmptyTrash() int {
	n := len(d.trash)
	d.trash = nil
	return n
}
