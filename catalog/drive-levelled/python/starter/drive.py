"""Cloud file storage."""


class Drive:
    def __init__(self):
        pass  # your state here

    def add_file(self, path: str, size: int) -> bool:
        """Stores a file of size bytes at path. False if the path is taken or size < 0."""
        raise NotImplementedError

    def get_file_size(self, path: str) -> int:
        """The file's size, or -1 if there is no file at path."""
        raise NotImplementedError

    def copy_file(self, source: str, dest: str) -> bool:
        """Copies source to dest. False if source is missing or dest is taken."""
        raise NotImplementedError

    def delete_file(self, path: str) -> int:
        """Removes the file and returns its size; -1 if there is none."""
        raise NotImplementedError
