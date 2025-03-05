from os import environ

import click

from leettools.common.logging import logger


@click.command()
@click.option(
    "-h",
    "--host",
    "host",
    default="0.0.0.0",
    required=False,
    help="The host ip address to run the app",
    show_default=True,
)
@click.option(
    "-p",
    "--port",
    "port",
    default=8000,
    required=False,
    help="The port to run the app",
    show_default=True,
)
@click.option(
    "-l",
    "--log-level",
    "log_level",
    default="INFO",
    required=False,
    type=click.Choice(
        [
            "INFO",
            "DEBUG",
            "WARNING",
            "ERROR",
        ],
        case_sensitive=False,
    ),
    help="the default log level for all loggers",
    show_default=True,
)
def start_service(
    host: str,
    port: int,
    log_level: str,
):
    from leettools.common.logging import EventLogger
    from leettools.context_manager import ContextManager
    from leettools.eds.scheduler.scheduler_manager import SchedulerManager
    from leettools.svc.api_service import APIService

    EventLogger.set_global_default_level(log_level.upper())
    logger().info(f"Log level set to {log_level.upper()}")
    context = ContextManager().get_context()
    scheduler = SchedulerManager(context).get_scheduler()
    scheduler.start()

    try:
        my_service = APIService(context.settings)
        my_service.run(host=host, port=port)
    finally:
        scheduler.shutdown()


if __name__ == "__main__":

    # set the env variable INIT_STRATEGY_STORE to True
    environ["INIT_STRATEGY_STORE"] = "true"
    start_service()
