FROM archlinux:base

# Minimal Arch sandbox image to manually test the setup.
# - provides pacman + makepkg tooling (base-devel)
# - creates an unprivileged user with passwordless sudo so `sudo -n` works
# - copies this repo into the user's home so you can run install commands manually

RUN pacman -Sy --noconfirm --needed \
    base-devel \
    git \
    make \
    sudo \
    python \
    python-pip \
    && pacman -Scc --noconfirm

# Passwordless sudo for the test user (so our code can use `sudo -n`).
RUN useradd -m -s /bin/bash tester \
    && echo "tester ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/tester \
    && chmod 0440 /etc/sudoers.d/tester

USER tester

WORKDIR /home/tester/personal-os-setup

# COPY --chown=tester:tester . /home/tester/personal-os-setup
# Mount local repo folder as a volume
VOLUME /home/tester/personal-os-setup

# Helpful default so running the container drops you into the repo.
CMD ["bash"]
