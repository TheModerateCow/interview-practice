package mini

import (
	"reflect"
	"testing"
)

func Test_p1_empty(t *testing.T) {
	got := Merge(nil)
	if got == nil || len(got) != 0 {
		t.Fatalf("want empty non-nil slice, got %#v", got)
	}
}

func Test_p1_overlap(t *testing.T) {
	got := Merge([]Interval{{1, 3}, {2, 6}, {8, 10}})
	want := []Interval{{1, 6}, {8, 10}}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("got %v want %v", got, want)
	}
}

func Test_p1_touching(t *testing.T) {
	got := Merge([]Interval{{1, 3}, {3, 5}})
	want := []Interval{{1, 5}}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("got %v want %v", got, want)
	}
}

func Test_p1_unsorted_and_contained(t *testing.T) {
	got := Merge([]Interval{{8, 9}, {1, 10}, {2, 3}, {20, 21}})
	want := []Interval{{1, 10}, {20, 21}}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("got %v want %v", got, want)
	}
}

func Test_p1_input_not_modified(t *testing.T) {
	in := []Interval{{5, 6}, {1, 2}}
	Merge(in)
	if in[0] != (Interval{5, 6}) || in[1] != (Interval{1, 2}) {
		t.Fatalf("input modified: %v", in)
	}
}
