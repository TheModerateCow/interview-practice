"""grade.prune drops the Go/Java hidden tests a -k filter excludes (so tests for unreached levels can't break the build).
Run: python3 tests/unit/test_prune.py"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from sandbox.grade import prune  # noqa: E402

GO = """package x

func Test_p1_a(t *testing.T) {
	if f() != 1 {
		t.Fatal("x")
	}
}

func Test_p2_a(t *testing.T) { t.Log("one-liner") }

func Test_p2_b(t *testing.T) {
	g()
}
"""
out = prune(GO, "go", "test_p1_", False)
assert "Test_p1_a" in out and "Test_p2" not in out and 't.Fatal("x")' in out and "g()" not in out, out
out = prune(GO, "go", "test_p1_", True)   # "not test_p1_"
assert "Test_p1_a" not in out and "Test_p2_a" in out and "Test_p2_b" in out and "g()" in out, out
assert prune(GO, "go", "TEST_P2_", False).count("func ") == 2   # case-insensitive, like -k
print("PASS go: keeps the selected tests whole, drops the rest (one-liners too)")

JAVA = """public class HiddenTest {
    static void test_p1_a() {
        Expect.eq(1, 1);
    }
    public static void test_p2_a() {
        if (true) {
        }
    }
}
"""
out = prune(JAVA, "java", "test_p1_", False)
assert "test_p1_a" in out and "test_p2_a" not in out and out.rstrip().endswith("}") and out.count("{") == out.count("}"), out
out = prune(JAVA, "java", "test_p1_", True)
assert "test_p1_a" not in out and "if (true)" in out and out.count("{") == out.count("}"), out
print("PASS java: a test ends at the } with its own indent")
