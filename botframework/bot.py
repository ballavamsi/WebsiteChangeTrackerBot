from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler, filters
    )
from .actions import Actions
from helpers.constants import ACCESS_TOKEN

import os


class Bot:
    def __init__(self):
        app = ApplicationBuilder().token(ACCESS_TOKEN).build()
        action = Actions()
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", action.start)],
            states={
                action.ADD: [MessageHandler(filters.TEXT,
                                            action.add_tracking)],
                action.TRACK: [MessageHandler(filters.TEXT,
                                              action.add_tracking)],
                action.TRACK_TYPE: [MessageHandler(filters.TEXT,
                                                   action.set_tracking_type)],
                action.LIST: [MessageHandler(filters.TEXT,
                                             action.list_tracking)],
                action.REENTER: [MessageHandler(filters.TEXT,
                                                action.add_tracking)],
            },
            fallbacks=[CommandHandler("cancel", action.cancel)]
        )

        add_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("add", action.add_tracking_begin)],
            states={
                action.TRACK: [MessageHandler(filters.TEXT,
                                              action.add_tracking)],
                action.TRACK_TYPE: [MessageHandler(filters.TEXT,
                                                   action.set_tracking_type)],
                action.LIST: [MessageHandler(filters.TEXT,
                                             action.list_tracking)],
                action.REENTER: [MessageHandler(filters.TEXT,
                                                action.add_tracking_begin)],
            },
            fallbacks=[CommandHandler("cancel", action.cancel)],
        )

        del_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("del", action.stop_tracking_begin)],
            states={
                action.DELETE: [MessageHandler(filters.TEXT,
                                               action.stop_tracking)],
                action.LIST: [MessageHandler(filters.TEXT,
                                             action.list_tracking)],
                action.REENTER: [MessageHandler(filters.TEXT,
                                                action.stop_tracking_begin)],
            },
            fallbacks=[CommandHandler("cancel", action.cancel)],
            allow_reentry=True
        )

        screenshot_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("screenshot",
                                         action.screenshot_begin)],
            states={
                action.SCREENSHOT: [MessageHandler(filters.TEXT,
                                                   action.screenshot)],
                action.LIST: [MessageHandler(filters.TEXT,
                                             action.list_tracking)],
                action.REENTER: [MessageHandler(filters.TEXT,
                                                action.screenshot_begin)],
            },
            fallbacks=[CommandHandler("cancel", action.cancel)],
            allow_reentry=True
        )

        app.add_handler(conv_handler)
        app.add_handler(add_conv_handler)
        app.add_handler(del_conv_handler)
        app.add_handler(screenshot_conv_handler)
        app.add_handler(CommandHandler("list", action.list_tracking))
        app.add_handler(CommandHandler("help", action.help_info))
        app.add_handler(CommandHandler("beginjobs", action.begin_jobs))
        app.run_polling()

        if not os.path.exists("data"):
            os.makedirs("data")
