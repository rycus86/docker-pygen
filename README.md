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

## Templating

To generate the configuration files, the app uses Jinja2 templates.
Templates have access to the `containers` list containing a list of *running* Docker
containers wrapped as `models.ContainerInfo` objects on a `models.ContainerList`.

A small example from a template could look like this:

```
{% set server_name = 'test.example.com' %}
upstream {{ server_name }} {
    {% for container in containers
          if  container.networks.first_value.ip_address
          and container.ports.tcp.first_value %}
        # {{ container.name }}
        server {{ container.networks.first_value.ip_address }}:{{ container.ports.tcp.first_value }};
    {% endfor %}
}
```

This example from the `nginx.example` file would output `server_name` as the value set
on the first line then iterate through the containers having an IP address and TCP port
exposed to finally output them prefixed with the container's name.

The available properties on a `models.ContainerInfo` object are:
- `raw`: The original container object from __docker-py__
- `id`: The container's ID
- `short_id`: The container's short ID
- `name`: The container's name
- `image`: The name of the image the container uses
- `status`: The current status of the container
- `labels`: The labels of the container (as `EnhancedDict` - see below)
- `env`: The environment variables of the container as `EnhancedDict`
- `networks`: The list of networks the container is attached to (as `NetworkList`)
- `ports`: The list of ports exposed by the container as `EnhancedDict` having
  `tcp` and `udp` ports as `EnhancedList`

The `utils.EnhancedDict` class is a Python dictionary extension to allow referring to
keys in it as properties - for example: `container.ports.tcp` instead of
`container['ports']['tcp']`. Property names are also case-insensitive.  
The `models.ContainerInfo` class extends `utils.EnhancedDict` to provide these features.

The `utils.EnhancedList` class is a Python list extension having additional properties
for getting the `first` or `last` element and the `first_value` - e.g. the first element
that is not `None` or empty.

The `models.ResourceList` extends `EnhancedList` to provide a `matching(target)` method
that allows getting the first element of the list having a matching ID or name.
The `models.ContainerList` extends the `matching` method to also match by Compose
service name for containers.
The `models.NetworkList` class adds matching by network ID.

Apart from the built-in Jinja template filters the `any` and `all` filters are also
available to evaluate conditions using the Python built-in functions with the same name.

## Updating the target file

The application listens for Docker *start*, *stop* and *die* events from containers
and schedules an update.
If the generated content didn't change and the target already has the same content
then the process stops.

If the template and the runtime information produces changes in the target file's
content then a notification is scheduled according to the intervals set at startup.
If there is another notification scheduled before the minimum interval is reached
then it is being rescheduled unless the time since the first generation has passed
the maximum interval already.
This ensures batching notifications together in case many events arrive close to each other.
See the `timer.NotificationTimer` class for implementation details.

## Signalling others

When the contents of the target file have changed the application can either restart
containers or send UNIX signals to them to let them know about the change.
Matching containers is done as described on the help text of the `--restart` argument.

For example if we have a couple of containers running with the service name `nginx`
managed by a Compose project, a `--signal nginx HUP` command would send a *SIGHUP*
signal to each of them to get them to reload their configuration.

## Swarm mode

Supporting Swarm mode and services is planned but is __not working yet__.

Services can be queried using the `api.DockerApi.services()` method but it is not
exposed to the template engine.
Notifications also don't work for Swarm services as I haven't found a clean way
of restarting (or signalling) them yet using *docker-py*.

## Acknowledgement

This tool was inspired by the awesome [jwilder/docker-gen](https://github.com/jwilder/docker-gen)
project that is written in Go and uses Go templates for configuration generation.
Many of the functionalities here match or are related to what's available there.

