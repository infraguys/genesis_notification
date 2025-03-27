#!/usr/bin/env bash

# Copyright 2025 Genesis Corporation
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

set -eu
set -x
set -o pipefail


GC_PATH="/opt/genesis_notification"
GC_CFG_DIR=/etc/genesis_notification
VENV_PATH="$GC_PATH/.venv"
BOOTSTRAP_PATH="/var/lib/genesis/bootstrap/scripts"

GC_PG_USER="genesis_notification"
GC_PG_PASS="pass"
GC_PG_DB="genesis_notification"

SYSTEMD_SERVICE_DIR=/etc/systemd/system/

# Install packages
sudo apt update
sudo apt dist-upgrade -y
sudo apt install -y \
    postgresql \
    libev-dev

# Default creds for genesis notification services
sudo -u postgres psql -c "CREATE ROLE $GC_PG_USER WITH LOGIN PASSWORD '$GC_PG_PASS';"
sudo -u postgres psql -c "CREATE DATABASE $GC_PG_USER OWNER $GC_PG_DB;"

# Install genesis core
sudo mkdir -p $GC_CFG_DIR
sudo cp "$GC_PATH/etc/genesis_notification/genesis_notification.conf" $GC_CFG_DIR/
sudo cp "$GC_PATH/etc/genesis_notification/logging.yaml" $GC_CFG_DIR/

mkdir -p "$VENV_PATH"
python3 -m venv "$VENV_PATH"
source "$GC_PATH"/.venv/bin/activate
pip install pip --upgrade
pip install -r "$GC_PATH"/requirements.txt
pip install -e "$GC_PATH"

# Apply migrations
ra-apply-migration --config-dir "$GC_PATH/etc/genesis_notification/" --path "$GC_PATH/migrations"
deactivate

# Create links to venv
sudo ln -sf "$VENV_PATH/bin/genesis-notification-mail-agent" "/usr/bin/genesis-notification-mail-agent"
sudo ln -sf "$VENV_PATH/bin/genesis-notification-builder-agent" "/usr/bin/genesis-notification-builder-agent"
sudo ln -sf "$VENV_PATH/bin/genesis-notification-user-api" "/usr/bin/genesis-notification-user-api"

# Install Systemd service files
sudo cp "$GC_PATH/etc/systemd/genesis-notification-mail-agent.service" $SYSTEMD_SERVICE_DIR
sudo cp "$GC_PATH/etc/systemd/genesis-notification-builder-agent.service" $SYSTEMD_SERVICE_DIR
sudo cp "$GC_PATH/etc/systemd/genesis-notification-user-api.service" $SYSTEMD_SERVICE_DIR

# Enable genesis notification services
sudo systemctl enable \
    genesis-notification-mail-agent \
    genesis-notification-builder-agent \
    genesis-notification-user-api