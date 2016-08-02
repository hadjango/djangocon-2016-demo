#!/bin/sh
# If running within docker-machine, the current directory will be a mounted
# volume, owned by the user running Docker on the host machine.
#
# In that case, we don't want to trample all over the contents of this
# directory with files owned by root. So we create a new user with the same
# UID, and drop privileges before running any commands.
#
# If we are not running in docker-machine, we create a user with uid 1000
# and execute commands as that user.

# Get the numeric user ID of the current directory.
uid=$(ls -nd . | awk '{ print $3 }')
gid=$(ls -nd . | awk '{ print $4 }')

# If the current working directory is owned by root, that means we're running
# with plain-old docker, not docker-machine.
if [ "$uid" == "0" ]; then
    uid=1000
    gid=1000
fi

group_name=$(getent group $gid)

groupadd -g 1000 olympia

# Create an `olympia` user with that ID, and the current directory
# as its home directory.
if [ -z "$group_name" ]; then
    useradd -Md $(pwd) -u $uid -g $gid -G olympia olympia
else
    useradd -Md $(pwd) -u $uid -g $gid olympia
fi

if [ ! -d /deps ]; then
    mkdir /deps
    chown $uid:$gid /deps
fi

mkdir -p /var/run/supervisor
chown $uid:$gid /var/run/supervisor
chown $uid:$gid /var/run/uwsgi

# Switch to that user and execute our actual command.
exec su root -c 'exec "$@"' sh -- "$@"
