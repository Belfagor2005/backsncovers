#!/bin/bash
## setup command=wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/backsncovers/main/installer.sh -O - | /bin/sh

version='1.3'
changelog='\nAdd ChannelUp / ChannelDown in Player\nFix major'
TMPPATH=/tmp/backsncovers-main
FILEPATH=/tmp/backsncovers.tar.gz

if [ ! -d /usr/lib64 ]; then
    PLUGINPATH=/usr/lib/enigma2/python/Plugins/Extensions/backsNcovers
else
    PLUGINPATH=/usr/lib64/enigma2/python/Plugins/Extensions/backsNcovers
fi

if [ -f /var/lib/dpkg/status ]; then
    STATUS=/var/lib/dpkg/status
    OSTYPE=DreamOs
else
    STATUS=/var/lib/opkg/status
    OSTYPE=Dream
fi

# Install wget if missing
if ! command -v wget >/dev/null 2>&1; then
    if [ "$OSTYPE" = "DreamOs" ]; then
        apt-get update && apt-get install -y wget || { echo "Failed to install wget"; exit 1; }
    else
        opkg update && opkg install wget || { echo "Failed to install wget"; exit 1; }
    fi
fi

# Detect Python version and set requests package name
if python --version 2>&1 | grep -q '^Python 3\.'; then
    PYTHON=PY3
    Packagerequests=python3-requests
else
    PYTHON=PY2
    Packagerequests=python-requests
fi

# Install python requests package if missing
if ! grep -qs "Package: $Packagerequests" "$STATUS"; then
    if [ "$OSTYPE" = "DreamOs" ]; then
        apt-get update && apt-get install -y "$Packagerequests" || { echo "Failed to install $Packagerequests"; exit 1; }
    else
        opkg update && opkg install "$Packagerequests" || { echo "Failed to install $Packagerequests"; exit 1; }
    fi
fi

mkdir -p "$TMPPATH" || exit 1
cd "$TMPPATH" || exit 1

# Download plugin archive
wget --no-check-certificate 'https://github.com/Belfagor2005/backsncovers/archive/refs/heads/main.tar.gz' -O "$FILEPATH" || {
    echo "Download failed"; exit 1;
}

# Extract archive
tar -xzf "$FILEPATH" -C /tmp/ || {
    echo "Extraction failed"; exit 1;
}

# Copy files to system
cp -r /tmp/backsncovers-main/usr/ / || {
    echo "Copy failed"; exit 1;
}

# Verify plugin installation
if [ ! -d "$PLUGINPATH" ]; then
    echo "Installation failed: $PLUGINPATH missing"
    rm -rf "$TMPPATH" "$FILEPATH" /tmp/backsncovers-main
    exit 1
fi

# Cleanup temporary files
rm -rf "$TMPPATH" "$FILEPATH" /tmp/backsncovers-main
sync

# System info
box_type=$(head -n 1 /etc/hostname 2>/dev/null || echo "Unknown")
FILE="/etc/image-version"
distro_value=$(grep '^distro=' "$FILE" 2>/dev/null | awk -F '=' '{print $2}')
distro_version=$(grep '^version=' "$FILE" 2>/dev/null | awk -F '=' '{print $2}')
python_vers=$(python --version 2>&1)

echo "#########################################################
#           backsNcovers $version INSTALLED SUCCESSFULLY     #
#########################################################
BOX MODEL: $box_type
PYTHON: $python_vers
IMAGE: ${distro_value:-Unknown} ${distro_version:-Unknown}"

sleep 3
# Restart Enigma2 or fallback to init restart sequence
if [ -f /usr/bin/enigma2 ]; then
    killall -9 enigma2
else
    init 4 && sleep 2 && init 3
fi

exit 0
