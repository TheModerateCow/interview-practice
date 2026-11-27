# gopls on the runner's own Go image (same toolchain and stdlib as a Run); +44 MB. Offline at run time.
FROM golang:1.27.4 AS build
RUN GOBIN=/out go install golang.org/x/tools/gopls@v0.24.0
FROM golang:1.27.4
COPY --from=build /out/gopls /usr/local/bin/gopls
