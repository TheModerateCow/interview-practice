"""Cloud file storage: files by path, folder listings, users with storage quotas, file versions and a trash."""


class Drive:
    def __init__(self):
        self.files = {}  # path -> {"owner": user_id or None, "versions": [size, ...]} (last = current)
        self.users = {}  # user_id -> {"capacity", "used"}
        self.trash = []  # (path, file) in deletion order

    def _charge(self, owner, size):
        """Counts size against owner's quota; False, changing nothing, if it doesn't fit. Unowned files are free."""
        if owner is None:
            return True
        u = self.users[owner]
        if u["used"] + size > u["capacity"]:
            return False
        u["used"] += size
        return True

    def _free(self, owner, size):
        if owner is not None:
            self.users[owner]["used"] -= size

    def _add(self, owner, path, size):
        if path in self.files or size < 0 or not self._charge(owner, size):
            return False
        self.files[path] = {"owner": owner, "versions": [size]}
        return True

    def _copy(self, owner, source, dest):
        if source not in self.files or dest in self.files:
            return False
        return self._add(owner, dest, self.files[source]["versions"][-1])

    # ---------------------------------------------------------------- level 1

    def add_file(self, path: str, size: int) -> bool:
        return self._add(None, path, size)

    def get_file_size(self, path: str) -> int:
        f = self.files.get(path)
        return -1 if f is None else f["versions"][-1]

    def copy_file(self, source: str, dest: str) -> bool:
        return source in self.files and self._copy(self.files[source]["owner"], source, dest)

    def delete_file(self, path: str) -> int:
        f = self.files.pop(path, None)
        if f is None:
            return -1
        self._free(f["owner"], sum(f["versions"]))
        self.trash.append((path, f))
        return f["versions"][-1]

    # ---------------------------------------------------------------- level 2

    def _under(self, prefix):
        return [(p, f["versions"][-1]) for p, f in self.files.items() if p.startswith(prefix)]

    def largest_files(self, prefix: str, n: int) -> list[str]:
        order = sorted(self._under(prefix), key=lambda ps: (-ps[1], ps[0]))
        return [f"{p}({s})" for p, s in order[: max(n, 0)]]

    def folder_size(self, prefix: str) -> int:
        return sum(s for _, s in self._under(prefix))

    # ---------------------------------------------------------------- level 3

    def add_user(self, user_id: str, capacity: int) -> bool:
        if user_id in self.users or capacity <= 0:
            return False
        self.users[user_id] = {"capacity": capacity, "used": 0}
        return True

    def add_file_by(self, user_id: str, path: str, size: int) -> int:
        if user_id not in self.users or not self._add(user_id, path, size):
            return -1
        return self.remaining(user_id)

    def copy_file_by(self, user_id: str, source: str, dest: str) -> int:
        if user_id not in self.users or not self._copy(user_id, source, dest):
            return -1
        return self.remaining(user_id)

    def remaining(self, user_id: str) -> int:
        u = self.users.get(user_id)
        return -1 if u is None else u["capacity"] - u["used"]

    # ---------------------------------------------------------------- level 4

    def overwrite_file(self, path: str, size: int) -> int:
        f = self.files.get(path)
        if f is None or size < 0 or not self._charge(f["owner"], size):
            return -1
        f["versions"].append(size)
        return len(f["versions"])

    def restore_version(self, path: str, version: int) -> int:
        f = self.files.get(path)
        if f is None or not 1 <= version <= len(f["versions"]):
            return -1
        self._free(f["owner"], sum(f["versions"][version:]))
        del f["versions"][version:]
        return f["versions"][-1]

    def restore_file(self, path: str) -> bool:
        if path in self.files:
            return False
        for i in range(len(self.trash) - 1, -1, -1):
            p, f = self.trash[i]
            if p == path:
                if not self._charge(f["owner"], sum(f["versions"])):
                    return False
                del self.trash[i]
                self.files[path] = f
                return True
        return False

    def empty_trash(self) -> int:
        n = len(self.trash)
        self.trash = []
        return n
