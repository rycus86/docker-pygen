# docker-pygen

*Work in progress...*

## Usage

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
                        be used for both MIN and MAX
  --debug               Enable debug log messages
```