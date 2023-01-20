from botframework.bot import Bot
from helpers.logging import logger
import traceback


def main():
    try:
        logger.info("Starting bot...")
        b = Bot()
    except Exception as e:
        logger.error(e)
        traceback.print_exc()
        logger.error("Restarting bot...")
        main()


if __name__ == "__main__":
    main()
