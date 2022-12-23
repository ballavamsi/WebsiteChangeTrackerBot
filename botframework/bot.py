from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler, filters,
    JobQueue,
    Updater
    )
from .actions import Actions
from helpers.constants import ACCESS_TOKEN

import os
import asyncio


class Bot:
    def __init__(self):
        action = Actions()

        app_builder = ApplicationBuilder().token(ACCESS_TOKEN)
        app = app_builder.build()

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", action.start)],
            states={
                action.ADD: [MessageHandler(filters.TEXT,
                                            action.add_tracking)],
                action.TRACK: [MessageHandler(filters.TEXT,
                                              action.add_tracking)],
                action.TRACK_TYPE: [MessageHandler(filters.TEXT,
                                                   action.set_tracking_type)],
                action.INTERVAL: [MessageHandler(filters.TEXT,
                                                 action.set_interval)],
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
                action.INTERVAL: [MessageHandler(filters.TEXT,
                                                 action.set_interval)],
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
                action.REENTER: [MessageHandler(filters.TEXT,
                                                action.screenshot_begin)],
            },
            fallbacks=[CommandHandler("cancel", action.cancel)],
            allow_reentry=True
        )

        compare_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("compare",
                                         action.instant_compare_begin)],
            states={
                action.INSTANT_COMPARE: [MessageHandler(
                    filters.TEXT,
                    action.instant_compare)],
                action.REENTER: [MessageHandler(filters.TEXT,
                                                action.instant_compare_begin)],
            },
            fallbacks=[CommandHandler("cancel", action.cancel)],
            allow_reentry=True
        )

        feedback_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("feedback",
                                         action.add_feedback_begin)],
            states={
                action.FEEDBACK: [MessageHandler(filters.TEXT,
                                                 action.add_feedback)],
                action.REENTER: [MessageHandler(filters.TEXT,
                                                action.add_feedback_begin)],
            },
            fallbacks=[CommandHandler("cancel", action.cancel)],
            allow_reentry=True
        )

        admin_conv_handler = ConversationHandler(
            entry_points=[CommandHandler(
                            "admin",
                            action.admin_commands_begin)],
            states={
                action.ADMIN_COMMANDS: [MessageHandler(filters.TEXT,
                                                       action.admin_commands)],
                action.BEGIN_JOBS: [MessageHandler(filters.TEXT,
                                                   action.begin_jobs)],
                action.STOP_JOBS: [MessageHandler(filters.TEXT,
                                                  action.stop_jobs)],
                action.LIST_FEEDBACKS: [MessageHandler(filters.TEXT,
                                                       action.list_feedbacks)],
                action.LIST_USERS: [MessageHandler(filters.TEXT,
                                                   action.list_users)],
                action.USERS_COUNT: [MessageHandler(filters.TEXT,
                                                    action.users_count)],
                action.REENTER: [MessageHandler(filters.TEXT,
                                                action.admin_commands_begin)],
            },
            fallbacks=[CommandHandler("cancel", action.cancel)],
            allow_reentry=True
        )

        app.add_handler(conv_handler)
        app.add_handler(add_conv_handler)
        app.add_handler(del_conv_handler)
        app.add_handler(screenshot_conv_handler)
        app.add_handler(compare_conv_handler)
        app.add_handler(feedback_conv_handler)
        app.add_handler(admin_conv_handler)
        app.add_handler(CommandHandler("list", action.list_tracking))
        app.add_handler(CommandHandler("help", action.help_info))

        jobs = JobQueue()
        jobs.set_application(app)
        _total, jq = action.create_job_queue_list(jobs)
        app.job_queue = jq

        app.run_polling(stop_signals=None)
