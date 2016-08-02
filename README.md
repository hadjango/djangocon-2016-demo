# Django UWSGI deploy demo

This repository demonstrates the principles behind the talk “High-Availability
Django” given by Frankie Dintino of _The Atlantic_ at the 2016 Djangocon.

In order to simulate the deployment of a large-ish Django project, it uses the
source for [addons.mozilla.org](https://addons.mozilla.org/), [found
here](https://github.com/mozilla/addons-server).

## Running

In order to run this demo VM, Docker, Fabric, and VirtualBox must be
installed. Once installed, the VM can be provisioned by running (from the
root of the checked out repository):

```shell
git submodule init
git submodule update
# Skip the next two steps if you don't want docker-machine
docker-machine create --driver virtualbox addons
eval $(docker-machine env addons)
docker-compose up -d
fab init
```

During the `fab init` step you will be prompted once when the database is initialized,
and then again to create the superuser.

Using `docker-machine` is not required unless you are using the older Docker Toolbox
on Mac (or you have installed it with `brew install docker`). Keep in mind however
that by default, running `docker-compose up` without using a docker-machine VM will
bind to port 80 on your localhost, so it will need to be unused, so you may wish
to use `docker-machine` even if you don't need to.
Alternatively, if you are using Docker for Mac, you can use
[https://github.com/nlf/dlite](https://github.com/nlf/dlite) to have docker use a
separate bridged network (and thus separate ips for its containers).

Grap the ip address using the command `fab ip` (unless you are not using `docker-machine`
or `dlite`, in which case it will be `127.0.0.1`), and then add to your `/etc/hosts` files:

```
192.168.64.7  live.addons stage.addons
```

Replacing `192.168.64.7` with the ip address for docker.

After running `fab init`, you should be able to visit http://live.addons/ and http://stage.addons/
to see the two initial builds (note that there may be a delay while the code initializes).
You can view a live-updating uwsgi status dashboard at http://live.addons/uwsgi/

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

## `fab init` and `fab create_build`

(Note: This repository's directory will be mounted as `/code` within the docker container,
so when you see paths like `/code/deploy/...` below, keep in mind that this refers also
to `./deploy/...` within this repository.)

Running `fab init` executes a number of steps to get a stage and live build up and running:

- Builds all of the requirements into wheels, output to /code/deploy/deps/wheelhouse, which
  then allows for faster `pip install` when creating new addons-server builds
- Creates two builds, “a” and “b”, in directories `/code/deploy/builds/{a,b}`
  (`fab create_build:a` and `fab create_build:b`). The `create_build` command
  does the following:

  - Creates symlinks for the static and media directories of the build so
    that nginx static serving works correctly.

      <sup>*Note*: All static assets (static files and user-uploaded media) live
      outside of the `builds` directory, in `/code/deploy/assets`. This is
      to allow for the common use case where static files and user media use
      a distinct mount or partition from the rest of the code. In order to
      keep all static file urls distinct (beyond whatever staticfile cache busting
      is used), the static files for all builds are kept in separate directories,
      e.g. `/code/deploy/assets/static/a`.</sup>

  - Uses `rsync` to copy the source in the `addons-server` submodule to the
    build directory, and copies the contents of `/code/src` on top of that.
  - From the build directory, runs `git init` and commits a randomly generated
    file. Mozilla’s addons-server uses the git commit hash to cache-bust minified
    assets, so this ensures that this step won’t fail and that the hash will be
    unique for each build.
  - Runs `npm install` as well as `pip install` with the requirements files, using
    the `--no-index` flag and our wheeldir of `code/deploy/deps/wheelhouse` to
    keep this speedy.
  - Runs `manage.py collectstatic` and `manage.py compress_assets` (the latter being a
    jingo-minify management command specific to the mozilla addons-server project)
    from the build’s virtualenv.
  - Determines what port number corresponds to the current build name, and creates
    `/code/deploy/builds/a/live.conf` and `/code/deploy/builds/a/stage.conf`, which
    are nginx configuration files that specify the upstream. This will only come
    into play if the build gets designated as the stage or live build (since nginx
    includes `/code/deploy/builds/_live/live.conf` and `/code/deploy/builds/_stage/stage.conf`).
  - Creates symlinks to the uwsgi skeleton file `/code/conf/uwsgi/vassal.skel` at
    `/code/deploy/builds/{a,b}/vassal.ini`. This step causes the uWSGI emperor to spawn
    a vassal that will manage the zerg instances. At this point the application on the
    ``web`` container will be listening on ports `2000` and `2010` (for the a and b builds,
    respectively), but because there are no zerg instances attached to the vassal
    http requests will not yet route.

- After the builds “a” and “b” are created and linked, respectively, to
  `/code/deploy/builds/_live` and `/code/deploy/builds/_stage`,
  `fab init` initiates the database and populates it with sample test data,
  executed using the manage.py in the `_live` (read “a”) build’s virtualenv.
- It then symlinks to the uwsgi skeleton file `/code/conf/uwsgi/zerg.skel` from
  `/code/deploy/builds/{a,b}/zerg.ini`. This “activates” (`fab activate:a`) the
  build, spawning zerg instances that attach to the vassal.
- Lastly, `nginx -s reload` is run on the nginx container, updating the upstreams.

## Troubleshooting

* Problem: You encounter the error “Error response from daemon: client is newer than server (client API version: 1.24, server API version: 1.22)”
* Solution: `export DOCKER_API_VERSION=1.22`
