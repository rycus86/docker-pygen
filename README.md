# docker-pygen

Configuration generator based on Docker containers state and parameters.

## Motivation

As we break our applications down to individual microservices more and more
the harder it gets to configure the supporting infrastructure around them.
If we think about managing HTTP proxying to them with servers like *Nginx*
or configuring any other system that has to know about a set of (or all)
of the running services - that can become quite an overhead done manually.

If you're using Docker to run those microservices then this project could
provide an easy solution to the problem.
By inspecting the currently running containers and their settings it can
generate configuration files for basically anything that works with those.
It can also notify other services about the configuration change by
signalling or restarting them.

## Usage

To run it as a Python application (tested on versions 2.7, 3.4 and 3.6)
clone the project and install the dependencies:

```shell
pip install -r requirements.txt
```

Then run it as `python cli.py <args>` where the arguments are:

```text
usage: arguments.py [-h] --template TEMPLATE [--target TARGET]
                    [--restart <CONTAINER>] [--signal <CONTAINER> <SIGNAL>]
                    [--interval <MIN> [<MAX> ...]] [--debug]

Template generator based on Docker runtime information

optional arguments:
  -h, --help            show this help message and exit
  --template TEMPLATE   The base Jinja2 template file or inline template as
                        string if it starts with "#"
  --target TARGET       The target to save the generated file (/dev/stdout by
                        default)
  --restart <CONTAINER>
                        Restart the target container, can be: ID, short ID,
                        name, Compose service name, label ["pygen.target"] or
                        environment variable ["PYGEN_TARGET"]
  --signal <CONTAINER> <SIGNAL>
                        Signal the target container, in <container> <signal>
                        format. The <container> argument can be one of the
                        attributes described in --restart
  --interval <MIN> [<MAX> ...]
                        Minimum and maximum intervals for sending
                        notifications. If there is only one argument it will
                        be used for both MIN and MAX. The defaults are: 0.5
                        and 2 seconds.
  --debug               Enable debug log messages
```

The application will need access to the Docker daemon too.

You can also run it as a Docker container to make things easier:

```shell
docker run -d --name config-generator                         \
              -v /var/run/docker.sock:/var/run/docker.sock:ro \
              -v shared-volume:/etc/share/config              \
              -v $PWD/template.conf:/etc/share/template.conf  \
              --template /etc/share/template.conf             \
              --target   /etc/share/config/auto.conf          \
              --restart  config-loader                        \
              --signal   web-server HUP                       \
              rycus86/docker-pygen
```

This command will:
- attach the Docker socket from `/var/run/docker.sock`
- attach a shared folder from the `shared-volume` to `/etc/share/config`
- attach the template file `template.conf` from the current host directory 
  to `/etc/share/template.conf`
- use the template (at `/etc/share/template.conf` inside the container)
- write to the `auto.conf` target file on the shared volume
  (at `/etc/share/config/auto.conf` inside the container)
- restart containers matching "config-loader" when the configuration file is updated
- send a *SIGHUP* signal to containers matching "web-server"

Matching containers can be based on container ID, short ID, name, Compose service name.
You can also add it as the value of the `pygen.target` label or as the value of the 
`PYGEN_TARGET` environment variable.

## TODO

- Templating

## Acknowledgement

This tool was inspired by the awesome [jwilder/docker-gen](https://github.com/jwilder/docker-gen)
project that is written in Go and uses Go templates for configuration generation.
Many of the functionalities here match or are related to what's available there.

