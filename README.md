# Django UWSGI deploy demo

This repository demonstrates the principles behind the talk “High-Availability
Django” given by Frankie Dintino of _The Atlantic_ at the 2016 Djangocon.

## Running

In order to run this demo VM, Docker, Fabric, and VirtualBox must be
installed. Once installed, the VM can be provisioned by running (from the
root of the checked out repository):

```shell
git submodule init
git submodule update
docker-machine create --driver virtualbox addons
eval $(docker-machine env addons)
docker-compose up -d
fab init
```

This will create two builds, “a”, and “b” (found in `deploy/builds/{a,b}`),
which are symlinked, respectively, to `deploy/builds/_live` and `deploy/builds/_stage`.

Grap the ip address using the command `fab ip`, and then add to your `/etc/hosts` files:

```
192.168.64.7  live.addons stage.addons
```

After running `fab init`, you should be able to visit http://live.addons/ and http://stage.addons/
to see the two initial builds. You can view a live-updating uwsgi status dashboard at
http://live.addons/uwsgi/

## Creating new builds

Builds are stored in folders, as part of the sequence {a, b, c, ..., z, aa, ab, ...}

In many scenarios, builds will cycle between a, b, and c, and the unused build
(the one linked neither to live or stage) can be removed or archived after each build.

To find the next unused build folder, run `fab find_free_build`. 

Then, to create the build, run, e.g. `fab create_build:z` where “z” should be
whatever build name was returned from `find_free_build`.

## Staging and deploying builds

To set a build as active (which will create a wsgi configuration that
spawns vassal in uWSGI emperor mode), run `fab activate:z`.

To then stage this build, run `fab stage:z` (again, the string after the “:”
being the build name), which will unlink the current stage build and link the
specified build to stage.

To “warm up” a build by hitting it with concurrent requests, use the command
`fab warmup:z` (the build name is optional and defaults to the stage build).

To swap the stage and live builds, run `fab swap_live`. By default, this will
swap live with the stage build, but it is possible to specify a different
build by, e.g. `fab swap_live:z`.

To spin down an old build (it cannot be the current live or stage builds), run
`fab deactivate:z`.

## Troubleshooting

* Problem: You encounter the error “Error response from daemon: client is newer than server (client API version: 1.24, server API version: 1.22)”
* Solution: `export DOCKER_API_VERSION=1.22`
