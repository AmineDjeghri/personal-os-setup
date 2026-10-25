# Arch Linux Docker test image

This folder provides a small **Arch Linux** Docker image intended as an **interactive sandbox**.
It copies the `personal-os-setup/` repo into the container user's home so you can jump in and run the setup manually.

## Build

From the `personal-os-setup/` directory:

```bash
docker build -f tests/archlinux/Dockerfile -t personal-os-setup-arch-test .
```

### Run (interactive) and mount

```bash
docker run --rm -it -v "$(pwd):/home/tester/personal-os-setup" personal-os-setup-arch-test
```

This drops you into `bash` in:

- `/home/tester/personal-os-setup`

From there you can try your normal workflow, for example:

```bash
make install
make run
```
