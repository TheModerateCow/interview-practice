# DropZone

The top of Home and the only way to import a set: drag a .zip anywhere onto the page. With no sets yet it fills the page.

- Provide: `.drop` with a `drop-big` headline ("Drop a set .zip here"), one line on where sets come from, and an error line (`err`) for a rejected zip with the server's message.
- While a file is dragged over the page, add `over` to the container: the border turns solid `fg` on `surface` ("Release to import" when a set is already open).
- No upload button, no file picker, no paste: drag-and-drop only.
