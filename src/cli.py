from arguments import parse_arguments
from pygen import PyGen
from utils import get_logger, set_log_level, setup_signals

logger = get_logger('pygen-cli')


def main():  # pragma: no cover
    logger.info('Starting docker-pygen ...')

    kwargs = parse_arguments().__dict__

    if kwargs.get('debug'):
        set_log_level('DEBUG')

    logger.debug('Startup arguments: %s', ', '.join('%s=%s' % item for item in kwargs.items()))

    app = PyGen(**kwargs)

    setup_signals(app)

    logger.debug('Signal handlers set up for SIGTERM, SIGINT and SIGHUP')

    try:
        app.update_target()

        logger.debug('Starting event watch loop')

        app.watch()

    except SystemExit:
        logger.info('Exiting...')
        
        raise

    finally:
        app.stop()


if __name__ == '__main__':  # pragma: no cover
    set_log_level('INFO')
    main()
