# Cloud drive

You're building the in-memory core of a cloud file storage service. It stores files by path, and later grows folder listings, users with storage quotas, file versions and a trash. The requirements arrive in **4 levels**. Each level opens when every test of the level before it passes, or when you press **Next part**.

Everything lives in the `{{Drive}}` type. Keep building on it: later levels add methods to it. Standard library only.

**Paths** are strings such as `"/docs/cv.pdf"`. There are no real folders: a path is just a name, and the drive doesn't check its format.

**Sizes** are integer numbers of bytes.

## Level 1: files

| Method | Behaviour |
|---|---|
| `{{add_file}}(path, size) → bool` | Stores a file of `size` bytes at `path`. Returns `false`, changing nothing, if a file already exists at `path` or `size < 0`. An empty file (`size = 0`) is fine. |
| `{{get_file_size}}(path) → int` | The size of the file at `path`, or `-1` if there is none. |
| `{{copy_file}}(source, dest) → bool` | Stores a copy of the file at `source` under `dest`. The copy is a separate file: deleting one leaves the other. Returns `false`, changing nothing, if there is no file at `source` or a file already exists at `dest` (so copying a file onto itself fails). |
| `{{delete_file}}(path) → int` | Removes the file at `path` and returns its size. `-1` if there is none. The path is then free for a new file. |

### Example

```
{{add_file}}("/docs/cv.pdf", 300)                  → true
{{add_file}}("/docs/cv.pdf", 500)                  → false   (path taken)
{{get_file_size}}("/docs/cv.pdf")                  → 300
{{copy_file}}("/docs/cv.pdf", "/backup/cv.pdf")     → true
{{copy_file}}("/docs/cv.pdf", "/backup/cv.pdf")     → false   (dest exists)
{{delete_file}}("/docs/cv.pdf")                    → 300
{{get_file_size}}("/docs/cv.pdf")                  → -1
{{get_file_size}}("/backup/cv.pdf")                → 300
```

## Checking your work

- **Run** checks your code against one example test per unlocked level and shows which fail and why.
- **Submit** runs the full hidden tests for every level you've unlocked. Passing them all opens the next level.
