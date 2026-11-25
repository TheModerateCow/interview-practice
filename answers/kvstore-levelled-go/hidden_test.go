package configstore

import (
	"strconv"
	"testing"
)

func hiddenItoa(n int) string { return strconv.Itoa(n) }

func hiddenEq[T comparable](t *testing.T, what string, got, want T) {
	t.Helper()
	if got != want {
		t.Fatalf("%s: got %v want %v", what, got, want)
	}
}

func hiddenSame(t *testing.T, what string, got, want []string) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("%s: got %q want %q", what, got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("%s: got %q want %q", what, got, want)
		}
	}
}

// opt turns a (value, ok) pair into the value, or "(none)" when there is no value.
func hiddenOpt(v string, ok bool) string {
	if !ok {
		return "(none)"
	}
	return v
}

// ---------------------------------------------------------------- level 1

func Test_l1_set_get_overwrite(t *testing.T) {
	s := NewStore()
	hiddenEq(t, "first set is new", s.Set(1, "svc-api", "replicas", "3"), true)
	hiddenEq(t, "get", hiddenOpt(s.Get(2, "svc-api", "replicas")), "3")
	hiddenEq(t, "overwrite is not new", s.Set(3, "svc-api", "replicas", "5"), false)
	hiddenEq(t, "get after overwrite", hiddenOpt(s.Get(4, "svc-api", "replicas")), "5")
	hiddenEq(t, "missing field", hiddenOpt(s.Get(5, "svc-api", "image")), "(none)")
	hiddenEq(t, "missing key", hiddenOpt(s.Get(6, "svc-web", "replicas")), "(none)")
}

func Test_l1_keys_and_fields_independent(t *testing.T) {
	s := NewStore()
	s.Set(1, "svc-api", "region", "eu-west")
	s.Set(2, "svc-web", "region", "us-east")
	s.Set(3, "svc-api", "tier", "gold")
	hiddenEq(t, "same field, other key", s.Set(4, "svc-web", "tier", "bronze"), true)
	hiddenEq(t, "api region", hiddenOpt(s.Get(5, "svc-api", "region")), "eu-west")
	hiddenEq(t, "web region", hiddenOpt(s.Get(6, "svc-web", "region")), "us-east")
	hiddenEq(t, "api tier", hiddenOpt(s.Get(7, "svc-api", "tier")), "gold")
	hiddenEq(t, "web tier", hiddenOpt(s.Get(8, "svc-web", "tier")), "bronze")
}

func Test_l1_delete(t *testing.T) {
	s := NewStore()
	s.Set(1, "db", "region", "eu-west")
	s.Set(2, "db", "size", "large")
	hiddenEq(t, "delete existing", s.Delete(3, "db", "region"), true)
	hiddenEq(t, "gone", hiddenOpt(s.Get(4, "db", "region")), "(none)")
	hiddenEq(t, "other field kept", hiddenOpt(s.Get(5, "db", "size")), "large")
	hiddenEq(t, "delete twice", s.Delete(6, "db", "region"), false)
	hiddenEq(t, "delete missing key", s.Delete(7, "cache", "region"), false)
	hiddenEq(t, "set after delete is new", s.Set(8, "db", "region", "us-east"), true)
	hiddenEq(t, "back", hiddenOpt(s.Get(9, "db", "region")), "us-east")
}

func Test_l1_delete_last_field(t *testing.T) {
	s := NewStore()
	s.Set(1, "db", "region", "eu-west")
	hiddenEq(t, "delete the only field", s.Delete(2, "db", "region"), true)
	hiddenEq(t, "nothing left to delete", s.Delete(3, "db", "region"), false)
	hiddenEq(t, "record can be refilled", s.Set(4, "db", "size", "small"), true)
	hiddenEq(t, "new field", hiddenOpt(s.Get(5, "db", "size")), "small")
	hiddenEq(t, "old field stays gone", hiddenOpt(s.Get(6, "db", "region")), "(none)")
}

func Test_l1_compare_and_set(t *testing.T) {
	s := NewStore()
	s.Set(1, "svc-api", "image", "v1")
	hiddenEq(t, "wrong expected", s.CompareAndSet(2, "svc-api", "image", "v0", "v2"), false)
	hiddenEq(t, "unchanged", hiddenOpt(s.Get(3, "svc-api", "image")), "v1")
	hiddenEq(t, "right expected", s.CompareAndSet(4, "svc-api", "image", "v1", "v2"), true)
	hiddenEq(t, "changed", hiddenOpt(s.Get(5, "svc-api", "image")), "v2")
	hiddenEq(t, "stale expected", s.CompareAndSet(6, "svc-api", "image", "v1", "v3"), false)
	hiddenEq(t, "still v2", hiddenOpt(s.Get(7, "svc-api", "image")), "v2")
}

func Test_l1_compare_and_set_missing_and_empty(t *testing.T) {
	s := NewStore()
	hiddenEq(t, "missing key, empty expected", s.CompareAndSet(1, "svc-api", "image", "", "v1"), false)
	hiddenEq(t, "still missing", hiddenOpt(s.Get(2, "svc-api", "image")), "(none)")
	s.Set(3, "svc-api", "note", "")
	hiddenEq(t, "empty string is a value", hiddenOpt(s.Get(4, "svc-api", "note")), "")
	hiddenEq(t, "missing field, empty expected", s.CompareAndSet(5, "svc-api", "image", "", "v1"), false)
	hiddenEq(t, "empty value matches empty expected", s.CompareAndSet(6, "svc-api", "note", "", "hi"), true)
	s.Delete(7, "svc-api", "note")
	hiddenEq(t, "deleted field", s.CompareAndSet(8, "svc-api", "note", "hi", "x"), false)
	hiddenEq(t, "new field with an empty value", s.Set(9, "svc-api", "blank", ""), true)
	hiddenEq(t, "set over an empty value is not new", s.Set(10, "svc-api", "blank", "y"), false)
}

// ---------------------------------------------------------------- level 2

func Test_l2_scan_sorted(t *testing.T) {
	s := NewStore()
	s.Set(1, "svc-api", "replicas", "3")
	s.Set(2, "svc-api", "image", "v1")
	s.Set(3, "svc-api", "env.PORT", "8080")
	s.Set(4, "svc-api", "tier", "gold")
	s.Set(5, "svc-web", "image", "w9")
	hiddenSame(t, "scan", s.Scan(6, "svc-api"), []string{"env.PORT=8080", "image=v1", "replicas=3", "tier=gold"})
	s.Set(7, "svc-api", "image", "v2")
	hiddenSame(t, "scan shows the latest value", s.Scan(8, "svc-api"), []string{"env.PORT=8080", "image=v2", "replicas=3", "tier=gold"})
}

func Test_l2_scan_missing_and_after_delete(t *testing.T) {
	s := NewStore()
	hiddenSame(t, "unknown key", s.Scan(1, "svc-api"), []string{})
	s.Set(2, "svc-api", "b", "2")
	s.Set(3, "svc-api", "a", "1")
	s.Delete(4, "svc-api", "b")
	hiddenSame(t, "deleted field left out", s.Scan(5, "svc-api"), []string{"a=1"})
	s.Delete(6, "svc-api", "a")
	hiddenSame(t, "all deleted", s.Scan(7, "svc-api"), []string{})
}

func Test_l2_scan_prefix(t *testing.T) {
	s := NewStore()
	s.Set(1, "svc-api", "env.PORT", "8080")
	s.Set(2, "svc-api", "env.HOST", "0.0.0.0")
	s.Set(3, "svc-api", "envoy", "on")
	s.Set(4, "svc-api", "image", "v1")
	s.Set(5, "svc-api", "env", "prod")
	hiddenSame(t, "env.", s.ScanPrefix(6, "svc-api", "env."), []string{"env.HOST=0.0.0.0", "env.PORT=8080"})
	hiddenSame(t, "env", s.ScanPrefix(7, "svc-api", "env"), []string{"env=prod", "env.HOST=0.0.0.0", "env.PORT=8080", "envoy=on"})
	hiddenSame(t, "whole field name", s.ScanPrefix(8, "svc-api", "image"), []string{"image=v1"})
	hiddenSame(t, "no match", s.ScanPrefix(9, "svc-api", "zz"), []string{})
	hiddenSame(t, "empty prefix is a scan", s.ScanPrefix(10, "svc-api", ""), s.Scan(11, "svc-api"))
	hiddenSame(t, "unknown key", s.ScanPrefix(12, "svc-web", "env"), []string{})
}

func Test_l2_prefix_is_not_substring(t *testing.T) {
	s := NewStore()
	s.Set(1, "svc-api", "export", "yes")
	s.Set(2, "svc-api", "port", "80")
	s.Set(3, "my-svc", "port", "81")
	s.Set(4, "svc", "port", "82")
	hiddenSame(t, "fields", s.ScanPrefix(5, "svc-api", "port"), []string{"port=80"})
	hiddenSame(t, "keys", s.ListKeys(6, "svc"), []string{"svc", "svc-api"})
}

func Test_l2_list_keys(t *testing.T) {
	s := NewStore()
	hiddenSame(t, "empty store", s.ListKeys(1, ""), []string{})
	s.Set(2, "svc-web", "a", "1")
	s.Set(3, "db-main", "a", "1")
	s.Set(4, "svc-api", "a", "1")
	s.Set(5, "svc-api", "b", "2")
	s.Set(6, "db-replica", "a", "1")
	hiddenSame(t, "all keys", s.ListKeys(7, ""), []string{"db-main", "db-replica", "svc-api", "svc-web"})
	hiddenSame(t, "svc-", s.ListKeys(8, "svc-"), []string{"svc-api", "svc-web"})
	hiddenSame(t, "db-r", s.ListKeys(9, "db-r"), []string{"db-replica"})
	hiddenSame(t, "no match", s.ListKeys(10, "cache"), []string{})
}

func Test_l2_list_keys_after_delete(t *testing.T) {
	s := NewStore()
	s.Set(1, "svc-api", "a", "1")
	s.Set(2, "svc-api", "b", "2")
	s.Set(3, "svc-web", "a", "1")
	s.Delete(4, "svc-api", "a")
	hiddenSame(t, "one field left", s.ListKeys(5, "svc"), []string{"svc-api", "svc-web"})
	s.Delete(6, "svc-api", "b")
	hiddenSame(t, "empty record not listed", s.ListKeys(7, "svc"), []string{"svc-web"})
	s.Set(8, "svc-api", "c", "3")
	hiddenSame(t, "listed again", s.ListKeys(9, "svc"), []string{"svc-api", "svc-web"})
}

// ---------------------------------------------------------------- level 3

func Test_l3_ttl_expiry_boundary(t *testing.T) {
	s := NewStore()
	hiddenEq(t, "new with ttl", s.SetWithTTL(10, "lock", "owner", "node-1", 5), true)
	hiddenEq(t, "live", hiddenOpt(s.Get(11, "lock", "owner")), "node-1")
	hiddenEq(t, "live just before expiry", hiddenOpt(s.Get(14, "lock", "owner")), "node-1")
	hiddenEq(t, "gone at expiry", hiddenOpt(s.Get(15, "lock", "owner")), "(none)")
	hiddenEq(t, "set after expiry is new", s.SetWithTTL(16, "lock", "owner", "node-2", 3), true)
	hiddenEq(t, "overwrite live is not new", s.SetWithTTL(17, "lock", "owner", "node-3", 3), false)
	hiddenEq(t, "new ttl counts from the overwrite", hiddenOpt(s.Get(19, "lock", "owner")), "node-3")
	hiddenEq(t, "and ends 3 after it", hiddenOpt(s.Get(20, "lock", "owner")), "(none)")
}

func Test_l3_remaining_ttl(t *testing.T) {
	s := NewStore()
	s.SetWithTTL(10, "lock", "owner", "node-1", 8)
	s.Set(11, "lock", "region", "eu")
	hiddenEq(t, "time left", s.RemainingTTL(12, "lock", "owner"), 6)
	hiddenEq(t, "one tick left", s.RemainingTTL(17, "lock", "owner"), 1)
	hiddenEq(t, "expired", s.RemainingTTL(18, "lock", "owner"), -1)
	hiddenEq(t, "no ttl", s.RemainingTTL(19, "lock", "region"), 0)
	hiddenEq(t, "missing field", s.RemainingTTL(20, "lock", "zone"), -1)
	hiddenEq(t, "missing key", s.RemainingTTL(21, "cache", "owner"), -1)
}

func Test_l3_set_and_cas_change_ttl(t *testing.T) {
	s := NewStore()
	s.SetWithTTL(10, "svc", "image", "v1", 10)
	hiddenEq(t, "set over a ttl field is not new", s.Set(12, "svc", "image", "v2"), false)
	hiddenEq(t, "set clears the ttl", s.RemainingTTL(13, "svc", "image"), 0)
	hiddenEq(t, "still there long after", hiddenOpt(s.Get(100, "svc", "image")), "v2")
	s.SetWithTTL(101, "svc", "image", "v3", 10)
	hiddenEq(t, "ttl added to a persistent field", s.RemainingTTL(102, "svc", "image"), 9)
	hiddenEq(t, "cas on a ttl field", s.CompareAndSet(105, "svc", "image", "v3", "v4"), true)
	hiddenEq(t, "cas keeps the expiry", s.RemainingTTL(106, "svc", "image"), 5)
	hiddenEq(t, "new value until expiry", hiddenOpt(s.Get(110, "svc", "image")), "v4")
	hiddenEq(t, "expired at the original time", hiddenOpt(s.Get(111, "svc", "image")), "(none)")
	hiddenEq(t, "cas on an expired field", s.CompareAndSet(112, "svc", "image", "v4", "v5"), false)
}

func Test_l3_expired_hidden_from_scans(t *testing.T) {
	s := NewStore()
	s.Set(1, "svc-api", "image", "v1")
	s.SetWithTTL(2, "svc-api", "canary", "on", 5)
	s.SetWithTTL(3, "svc-api", "env.DEBUG", "1", 10)
	s.Set(4, "svc-api", "env.PORT", "80")
	hiddenSame(t, "all live", s.Scan(5, "svc-api"), []string{"canary=on", "env.DEBUG=1", "env.PORT=80", "image=v1"})
	hiddenSame(t, "canary expired", s.Scan(7, "svc-api"), []string{"env.DEBUG=1", "env.PORT=80", "image=v1"})
	hiddenSame(t, "prefix before expiry", s.ScanPrefix(12, "svc-api", "env."), []string{"env.DEBUG=1", "env.PORT=80"})
	hiddenSame(t, "prefix after expiry", s.ScanPrefix(13, "svc-api", "env."), []string{"env.PORT=80"})
}

func Test_l3_expired_keys_not_listed(t *testing.T) {
	s := NewStore()
	s.SetWithTTL(1, "lock-a", "owner", "n1", 5)
	s.SetWithTTL(2, "lock-b", "owner", "n2", 10)
	s.SetWithTTL(3, "lock-b", "since", "2", 2)
	s.Set(4, "lock-c", "owner", "n3")
	hiddenSame(t, "all live", s.ListKeys(5, "lock-"), []string{"lock-a", "lock-b", "lock-c"})
	hiddenSame(t, "lock-a expired", s.ListKeys(6, "lock-"), []string{"lock-b", "lock-c"})
	hiddenSame(t, "lock-b keeps one live field", s.ListKeys(11, "lock-"), []string{"lock-b", "lock-c"})
	hiddenSame(t, "lock-b fully expired", s.ListKeys(12, "lock-"), []string{"lock-c"})
	hiddenSame(t, "nothing left to scan", s.Scan(13, "lock-b"), []string{})
}

func Test_l3_delete_and_reset_expired(t *testing.T) {
	s := NewStore()
	s.SetWithTTL(1, "lock", "owner", "n1", 4)
	hiddenEq(t, "delete live ttl field", s.Delete(2, "lock", "owner"), true)
	hiddenEq(t, "gone before expiry", hiddenOpt(s.Get(3, "lock", "owner")), "(none)")
	s.SetWithTTL(4, "lock", "owner", "n2", 4)
	hiddenEq(t, "delete expired field", s.Delete(8, "lock", "owner"), false)
	hiddenEq(t, "set over an expired field is new", s.Set(9, "lock", "owner", "n3"), true)
	hiddenEq(t, "persistent now", s.RemainingTTL(50, "lock", "owner"), 0)
}

// ---------------------------------------------------------------- level 4

func Test_l4_backup_restore(t *testing.T) {
	s := NewStore()
	s.Set(1, "svc-api", "image", "v1")
	s.Set(2, "svc-api", "replicas", "3")
	hiddenEq(t, "first backup", s.Backup(3), "b1")
	s.Set(4, "svc-api", "image", "v2")
	s.Delete(5, "svc-api", "replicas")
	s.Set(6, "svc-web", "image", "w1")
	hiddenEq(t, "unknown backup", s.Restore(7, "b2"), false)
	hiddenEq(t, "unknown backup changed nothing", hiddenOpt(s.Get(8, "svc-api", "image")), "v2")
	hiddenEq(t, "restore", s.Restore(9, "b1"), true)
	hiddenSame(t, "api back as it was", s.Scan(10, "svc-api"), []string{"image=v1", "replicas=3"})
	hiddenSame(t, "keys made later are gone", s.ListKeys(11, ""), []string{"svc-api"})
	hiddenEq(t, "second backup", s.Backup(12), "b2")
}

func Test_l4_restore_recalculates_ttl(t *testing.T) {
	s := NewStore()
	s.SetWithTTL(5, "lock", "owner", "n1", 10)
	s.Set(6, "lock", "region", "eu")
	s.Backup(8)
	hiddenEq(t, "expired after the backup", hiddenOpt(s.Get(20, "lock", "owner")), "(none)")
	s.Restore(50, "b1")
	hiddenEq(t, "back with the time it had left", s.RemainingTTL(51, "lock", "owner"), 6)
	hiddenEq(t, "live before the new expiry", hiddenOpt(s.Get(56, "lock", "owner")), "n1")
	hiddenEq(t, "expires 7 after the restore", hiddenOpt(s.Get(57, "lock", "owner")), "(none)")
	hiddenEq(t, "persistent stays persistent", s.RemainingTTL(58, "lock", "region"), 0)
}

func Test_l4_backup_skips_expired(t *testing.T) {
	s := NewStore()
	s.SetWithTTL(1, "lock-a", "owner", "n1", 3)
	s.SetWithTTL(2, "lock-b", "owner", "n2", 4)
	s.Set(3, "lock-b", "zone", "z1")
	hiddenEq(t, "backup with lock-a expired", s.Backup(4), "b1")
	s.Set(5, "lock-a", "owner", "n9")
	s.Restore(6, "b1")
	hiddenSame(t, "lock-a was expired at the backup", s.ListKeys(7, ""), []string{"lock-b"})
	hiddenEq(t, "lock-b owner had 2 left at the backup", s.RemainingTTL(7, "lock-b", "owner"), 1)
	hiddenSame(t, "so it expires 2 after the restore", s.Scan(8, "lock-b"), []string{"zone=z1"})
}

func Test_l4_backups_are_snapshots(t *testing.T) {
	s := NewStore()
	hiddenEq(t, "backup of an empty store", s.Backup(1), "b1")
	s.Set(2, "svc", "image", "v1")
	hiddenEq(t, "second", s.Backup(3), "b2")
	s.Restore(4, "b2")
	s.Set(5, "svc", "image", "v2")
	s.Set(6, "svc", "debug", "on")
	hiddenEq(t, "restore b2 again", s.Restore(7, "b2"), true)
	hiddenSame(t, "later edits did not reach the backup", s.Scan(8, "svc"), []string{"image=v1"})
	hiddenEq(t, "restore the empty backup", s.Restore(9, "b1"), true)
	hiddenSame(t, "store is empty", s.ListKeys(10, ""), []string{})
	hiddenEq(t, "restore a later backup after an earlier one", s.Restore(11, "b2"), true)
	hiddenEq(t, "value back", hiddenOpt(s.Get(12, "svc", "image")), "v1")
	hiddenEq(t, "ids keep counting", s.Backup(13), "b3")
}

func Test_l4_get_at(t *testing.T) {
	s := NewStore()
	s.Set(2, "svc", "image", "v1")
	s.Set(5, "svc", "image", "v2")
	s.Delete(8, "svc", "image")
	s.Set(12, "svc", "image", "v3")
	s.CompareAndSet(14, "svc", "image", "v3", "v4")
	for _, c := range []struct {
		at   int
		want string
	}{{1, "(none)"}, {2, "v1"}, {4, "v1"}, {5, "v2"}, {7, "v2"}, {8, "(none)"}, {11, "(none)"}, {12, "v3"}, {14, "v4"}, {20, "v4"}} {
		hiddenEq(t, "image at "+hiddenItoa(c.at), hiddenOpt(s.GetAt(20, "svc", "image", c.at)), c.want)
	}
	hiddenEq(t, "never set", hiddenOpt(s.GetAt(21, "svc", "zone", 21)), "(none)")
	hiddenEq(t, "unknown key", hiddenOpt(s.GetAt(22, "db", "image", 22)), "(none)")
}

func Test_l4_get_at_ttl_and_restore(t *testing.T) {
	s := NewStore()
	s.SetWithTTL(10, "lock", "owner", "n1", 5)
	s.Set(11, "lock", "zone", "z1")
	s.Backup(12)
	s.Set(20, "lock", "zone", "z2")
	s.Set(21, "lock", "extra", "x")
	s.Restore(30, "b1")
	hiddenEq(t, "owner live at 14", hiddenOpt(s.GetAt(40, "lock", "owner", 14)), "n1")
	hiddenEq(t, "owner expired at 15", hiddenOpt(s.GetAt(40, "lock", "owner", 15)), "(none)")
	hiddenEq(t, "owner back after the restore", hiddenOpt(s.GetAt(40, "lock", "owner", 30)), "n1")
	hiddenEq(t, "restored owner keeps 3 left", hiddenOpt(s.GetAt(40, "lock", "owner", 33)), "(none)")
	hiddenEq(t, "zone before the restore", hiddenOpt(s.GetAt(40, "lock", "zone", 29)), "z2")
	hiddenEq(t, "zone at the restore", hiddenOpt(s.GetAt(40, "lock", "zone", 30)), "z1")
	hiddenEq(t, "extra before the restore", hiddenOpt(s.GetAt(40, "lock", "extra", 29)), "x")
	hiddenEq(t, "extra removed by the restore", hiddenOpt(s.GetAt(40, "lock", "extra", 30)), "(none)")
}
