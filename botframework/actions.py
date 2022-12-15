from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    ConversationHandler,
    CallbackContext,
    ContextTypes
)
import validators
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pdb

from helpers.imageconverter import ImageConverter
from helpers.screenshot import Screenshot
from helpers.imagecompare import ImageComparer
from helpers.logging import logger
from helpers.db import DBHelper
from botframework.constants import *
import difflib

messages = {
    "start": "Hello %s",
    "add": "Please enter the url you want to track:"
    "\nex: https://ballavamsi.com",
    "add_success": "Tracking %s",
    "add_fail": "Tracking failed",
    "del": "Please enter the url you want to stop tracking",
    "del_id": "Please enter the ID of the url you want to stop tracking",
    "del_success": "Tracking stopped for %s",
    "del_fail": "Tracking stop failed",
    "list": "Please select the url you want to track",
    "list_display": "Tracking urls",
    "list_empty": "No tracking found",
    "list_fail": "List failed",
    "screenshot": "Please enter the url you want to take screenshot",
    "screenshot_id": "Please enter the ID of the url you want to take "
    "screenshot",
    "screenshot_success": "Screenshot taken",
    "screenshot_fail": "Failed to take screenshot for %s",
    "screenshot_change": "We have identified a change in the screenshot"
    " for %s",
    "screenshot_taken": "Here is the screenshot of %s",
    "screenshot_once": "Taking screenshot once",
    "screenshot_nochange": "No change in screenshot for %s",
    "api_nochange": "No change in api response for %s",
    "api_response": "API response captured\n%s",
    "api_error": "We didn't receive 200 from API - %s",
    "api_fail": "Failed to capture API response for %s",
    "api_change": "We have identified a change in the api response for %s",
    "track_type": "Please select the capture type to compare from "
    "options below",
    "track_type_fail": "Invalid type",
    "select_interval": "Please select the interval to check for changes",
    "invalid_interval": "Invalid interval",
    "default_interval": "Default interval set to 60 minutes",
    "invalid_url": "Invalid url",
    "invalid_type": "Invalid type",
    "invalid_id": "Invalid id",
    "reenter": "Invalid url",
    "cancel": "Cancelled",
    "blank_data": "You don't have anything in this space",
    "bye": "Bye! I hope we can talk again some day.",
    "jobs_started": "%s jobs started",
    "jobs_stopped": "%s jobs stopped",
    "add_feedback": "Please enter your feedback",
    "feedback_success": "Thank you for your feedback",
    "instant_compare": "Please enter the ID of url you want to compare",
}

minutes_options = {
    "15min": 15,
    "30min": 30,
    "60min": 60,
    "12hrs": 720,
    "1day": 1440
    }


class Actions:

    ADD, DELETE, TRACK, TRACK_TYPE, REENTER, SCREENSHOT, LIST, FEEDBACK,\
        INSTANT_COMPARE, INTERVAL = range(10)

    def __init__(self):
        self.image_converter = ImageConverter()
        self._db = DBHelper()

    async def create_user(self, update: Update):
        if self._db.fetch_user(update.message.from_user.id) is None:
            self._db.insert_user(update.message.from_user.id,
                                 update.message.from_user.first_name,
                                 update.message.from_user.username)
            logger.info(f"Created user {update.message.from_user.id}"
                        f" ({update.message.from_user.username})")
        else:
            logger.info(f"User {update.message.from_user.id}"
                        f" ({update.message.from_user.username}) exists")

    async def reply_msg(self, update: Update, *args, **kwargs):

        logger.info(f"Replying with {args[0]} "
                    f"to {update.message.from_user.id} "
                    f"({update.message.from_user.first_name})")

        if kwargs.get('reply_markup') is None:
            kwargs['reply_markup'] = ReplyKeyboardRemove()

        await update.message.reply_text(*args, **kwargs)

    async def commandsHandler(self, update: Update, context: CallbackContext):

        await self.create_user(update)
        logger.info(f"Received command {update.message.text} from "
                    f"{update.message.from_user.id} "
                    f"({update.message.from_user.first_name})")

        if update.message.text in ["/cancel"]:
            await self.reply_msg(update, messages["cancel"])
            return ConversationHandler.END
        return None

    async def start(self, update: Update, context: CallbackContext):

        await self.create_user(update)

        if await self.commandsHandler(update, context) is not None:
            return ConversationHandler.END
        await self.reply_msg(update,
                             messages["start"] %
                             update.message.from_user.first_name)
        await self.reply_msg(update, messages["add"])
        return self.TRACK

    async def add_tracking_begin(self, update: Update, context):
        if await self.commandsHandler(update, context) is not None:
            return ConversationHandler.END

        await self.reply_msg(update, messages["add"])
        return self.TRACK

    async def add_tracking(self, update: Update, context: CallbackContext):

        await self.create_user(update)

        if await self.commandsHandler(update, context) is not None:
            return ConversationHandler.END

        # check if url is valid
        if not validators.url(update.message.text):
            await self.reply_msg(update, messages["invalid_url"])
            return self.REENTER

        context.user_data['url'] = update.message.text
        await self.reply_msg(update,
                             messages["track_type"],
                             reply_markup=ReplyKeyboardMarkup(
                                [["screenshot", "api"]],
                                one_time_keyboard=True))

        return self.TRACK_TYPE

    async def stop_tracking_begin(self, update: Update, context):
        if await self.commandsHandler(update, context) is not None:
            return ConversationHandler.END
        urls = self._db.list_tracking(update.message.from_user.id)
        list_urls_msg = messages["del_id"]
        for url in urls:
            list_urls_msg += f"\nID: {url[0]}\n-> URL: {url[3]}" + \
                f"\n-> Capture Type: {url[4]}"
        await self.reply_msg(update,
                             list_urls_msg,
                             disable_web_page_preview=True)
        return self.DELETE

    async def stop_tracking(self, update: Update, context: CallbackContext):
        if await self.commandsHandler(update, context) is not None:
            return ConversationHandler.END

        track_data = self._db.fetch_tracking(update.message.text)
        user = self._db.fetch_user(update.message.from_user.id)

        if track_data is None:
            await self.reply_msg(update, messages["invalid_id"])
            return self.REENTER

        if user is None:
            await self.reply_msg(update, messages["blank_data"])
            return self.REENTER

        if str(update.message.from_user.id) != user[1]:
            await self.reply_msg(update, messages["invalid_id"])
            return self.REENTER

        # delete data files
        if os.getenv("USE_FILESYSTEM_TO_SAVE_IMAGES") == "True":
            if os.path.exists(f"{os.getenv('FILESYSTEM_PATH')}/"
                              f"screenshot_{track_data[0]}_old.png"):
                os.remove(f"{os.getenv('FILESYSTEM_PATH')}" +
                          f"/screenshot_{track_data[0]}_old.png")
            if os.path.exists(f"{os.getenv('FILESYSTEM_PATH')}/"
                              f"screenshot_{track_data[0]}_new.png"):
                os.remove(f"{os.getenv('FILESYSTEM_PATH')}/"
                          f"screenshot_{track_data[0]}_new.png")

        self._db.delete_tracking(update.message.text)
        self.remove_job_if_exists(str(track_data[0]), context)
        await self.reply_msg(update, messages["del_success"] % track_data[3])
        return ConversationHandler.END

    async def set_interval(self, update: Update, context: CallbackContext):
        if await self.commandsHandler(update, context) is not None:
            return ConversationHandler.END
        context.user_data['interval'] = update.message.text

        if not context.user_data['interval'] in minutes_options.keys():
            await self.reply_msg(update, messages["invalid_interval"])
            await self.reply_msg(update, messages["default_interval"])
            context.user_data['interval'] = "60min"

        new_id = await self.add_tracking_to_db(update, context)
        track_data = self._db.fetch_tracking(new_id)

        # add jobs to queue
        if context.user_data['type'] == "api":
            await self.reply_msg(update, "Calling API once")
            context.job_queue.run_once(
                self.call_api_once,
                2,
                chat_id=update.effective_message.chat_id,
                name='once_' + str(new_id),
                context=track_data
            )
            context.job_queue.run_repeating(
                self.check_api_and_compare,
                timedelta(
                 minutes=minutes_options[context.user_data['interval']]),
                chat_id=update.effective_message.chat_id,
                name=str(new_id),
                context=track_data)

        if context.user_data['type'] == 'screenshot':
            await self.reply_msg(update, "Taking screenshot once")
            context.job_queue.run_once(
                self.take_screenshot_once,
                2,
                chat_id=update.effective_message.chat_id,
                name='once_' + str(new_id),
                context=track_data
            )

            context.job_queue.run_repeating(
                self.take_screenshot_and_compare,
                timedelta(
                 minutes=minutes_options[context.user_data['interval']]),
                chat_id=update.effective_message.chat_id,
                name=str(new_id),
                context=track_data)

        return ConversationHandler.END

    async def set_tracking_type(self, update: Update,
                                context: CallbackContext):
        if await self.commandsHandler(update, context) is not None:
            return ConversationHandler.END
        context.user_data['type'] = update.message.text

        await self.reply_msg(update,
                             messages["select_interval"],
                             reply_markup=ReplyKeyboardMarkup(
                                [list(minutes_options.keys())],
                                one_time_keyboard=True))

        return self.INTERVAL

    async def add_tracking_to_db(self, update, context):
        new_id = self._db.insert_tracking(
                    update.message.from_user.id,
                    update.effective_message.chat_id,
                    context.user_data['url'],
                    context.user_data['type'],
                    minutes_options[context.user_data['interval']])
        logger.info("Added new tracking with id %s", new_id)
        await self.reply_msg(
                update,
                messages["add_success"] % context.user_data['url'],
                disable_web_page_preview=True)
        return new_id

    async def list_tracking(self, update: Update, context: CallbackContext):

        if await self.commandsHandler(update, context) is not None:
            return ConversationHandler.END

        urls = self._db.list_tracking(update.message.from_user.id)
        if type(urls) is str:
            await self.reply_msg(update, messages["blank_data"])
        else:
            await self.reply_msg(update, messages["list_display"])
            urls_list = ""
            for url in urls:
                urls_list = urls_list + f"ID: {url[0]}\n-> URL: {url[3]}" + \
                                f"\n-> Capture Type: {url[4]}" + \
                                f"\n-> Interval: {url[8]} minutes" + \
                                f"\n-> Last Run: {url[9]}\n"
            await self.reply_msg(update,
                                 urls_list,
                                 disable_web_page_preview=True)
        return ConversationHandler.END

    async def cancel(self, update: Update, context: CallbackContext):
        user = update.message.from_user
        logger.info("User %s canceled the conversation.", user.first_name)
        await self.reply_msg(update, messages["bye"])

        return ConversationHandler.END

    async def help_info(self, update: Update, context: CallbackContext):

        await self.create_user(update)
        await self.reply_msg(update, "You can enter below \
            commands\n/start - start tracking\
            \n/list - list tracking urls\
            \n/add - add tracking url\
            \n/del - delete tracking url\
            \n/help - help info\
            \n/screenshot - get screenshot of url\
            \n/compare - instantly compare\
            \n/feedback - provide feedback to ballavamsi\
            \n/cancel to cancel the current operation")

    async def instant_compare_begin(self, update: Update,
                                    context: CallbackContext):
        urls = self._db.list_tracking(update.message.from_user.id)
        list_urls_msg = messages["instant_compare"]
        for url in urls:
            list_urls_msg = list_urls_msg + f"\nID: {url[0]}\n-> URL: " + \
                f"{url[3]}\n-> Capture Type: {url[4]}"
        await self.reply_msg(update,
                             list_urls_msg,
                             disable_web_page_preview=True)
        return self.INSTANT_COMPARE

    async def instant_compare(self, update: Update, context: CallbackContext):

        if await self.commandsHandler(update, context) is not None:
            return ConversationHandler.END

        track_data = self._db.fetch_tracking(update.message.text)
        if track_data is None:
            await self.reply_msg(update, messages["invalid_id"])
            return ConversationHandler.END

        track_user = self._db.fetch_user(update.message.from_user.id)
        if track_data[1] != track_user[0]:
            await self.reply_msg(update, messages["invalid_id"])
            return ConversationHandler.END

        await self.reply_msg(update, "Instant Compare started")
        if track_data[4] == "api":
            context.job_queue.run_once(
                self.check_api_and_compare,
                2,
                chat_id=update.effective_message.chat_id,
                name='instant_' + str(track_data[0]),
                context=track_data
            )
        if track_data[4] == "screenshot":
            context.job_queue.run_once(
                self.take_screenshot_and_compare,
                2,
                chat_id=update.effective_message.chat_id,
                name='instant_' + str(track_data[0]),
                context=track_data
            )
        return ConversationHandler.END

    async def screenshot_begin(self, update: Update, context: CallbackContext):
        urls = self._db.list_tracking(update.message.from_user.id)
        list_urls_msg = messages["screenshot_id"]
        for url in urls:
            if url[4] == "screenshot":
                list_urls_msg = list_urls_msg + f"\nID: {url[0]}\n-> URL: " + \
                    f"{url[3]}\n-> Capture Type: {url[4]}"
        await self.reply_msg(update,
                             list_urls_msg,
                             disable_web_page_preview=True)
        return self.SCREENSHOT

    async def screenshot(self, update: Update, context: CallbackContext):

        if await self.commandsHandler(update, context) is not None:
            return ConversationHandler.END

        track_data = self._db.fetch_tracking(update.message.text)
        user = self._db.fetch_user(update.message.from_user.id)

        if track_data is None:
            await self.reply_msg(update, messages["invalid_id"])
            return self.REENTER

        if user is None:
            await self.reply_msg(update, messages["blank_data"])
            return self.REENTER

        if str(update.message.from_user.id) != user[1]:
            await self.reply_msg(update, messages["invalid_id"])
            return self.REENTER

        if track_data[4] != "screenshot":
            await self.reply_msg(update, messages["invalid_type"])
            return self.REENTER

        await self.reply_msg(update, "Taking screenshot once")
        context.job_queue.run_once(
            self.take_screenshot_once,
            2,
            chat_id=update.effective_message.chat_id,
            name='once_' + str(track_data[0]),
            context=track_data
        )
        return ConversationHandler.END

    async def add_feedback_begin(self, update: Update, context):

        await self.create_user(update)
        await self.reply_msg(update, messages["add_feedback"])
        return self.FEEDBACK

    async def add_feedback(self, update: Update, context: CallbackContext):

        if await self.commandsHandler(update, context) is not None:
            return ConversationHandler.END

        self._db.insert_feedback(update.message.from_user.id,
                                 update.message.text)
        await self.reply_msg(update, messages["feedback_success"])
        return ConversationHandler.END

    async def list_feedbacks(self, update: Update, context: CallbackContext):
        if await self.commandsHandler(update, context) is not None:
            return ConversationHandler.END

        if str(update.message.from_user.id) not in ADMIN_USERS:
            return ConversationHandler.END

        feedbacks = self._db.list_feedback()
        feedbacks_list = ""
        for feedback in feedbacks:
            feedback_user = self._db.fetch_user_by_id(feedback[1])
            feedbacks_list = \
                feedbacks_list + f"User: " + \
                f"{feedback_user[2]}" + \
                f"\n-> Feedback: {feedback[2]}\n" + \
                f"-> Date: {feedback[3]}\n"
        await self.reply_msg(update,
                             feedbacks_list,
                             disable_web_page_preview=True)

    # JOBS RELATED
    async def remove_job_if_exists(self, name: str, context: CallbackContext):
        current_jobs = context.job_queue.get_jobs_by_name(name)
        if current_jobs:
            for job in current_jobs:
                job.schedule_removal()

    async def take_screenshot_once(self, context: CallbackContext):
        track_data = context.job.context
        try:
            s = Screenshot(admin_user=str(track_data[2]) in ADMIN_USERS)
            temp_filename = s.capture(track_data[3], track_data[0])

            await context.bot.send_message(
                chat_id=track_data[2],
                text=f"{messages['screenshot_taken']}" % track_data[3],
                disable_web_page_preview=True)

            await context.bot.send_photo(
                chat_id=track_data[2],
                photo=open(temp_filename, 'rb'))
        except Exception as e:
            await context.bot.send_message(
                chat_id=track_data[2],
                text=f"{messages['screenshot_fail']}" % track_data[3],
                disable_web_page_preview=True)
            logger.error(e)

    async def take_screenshot_and_compare(self, context: CallbackContext):
        try:
            track_data = context.job.context

            # track_data = self._db.fetch_tracking(track_data[0])
            s = Screenshot(admin_user=str(track_data[2]) in ADMIN_USERS)
            temp_filename = s.capture(track_data[3], track_data[0])
            new_filename = temp_filename.replace('temp', 'new')
            old_filename = temp_filename.replace('temp', 'old')

            if os.getenv('USE_FILESYSTEM_TO_SAVE_IMAGES') == 'False':
                if track_data[5] is None:
                    old_image_content = self.image_converter.\
                                        convert_image_to_base64(temp_filename)
                    self._db.update_tracking(
                        track_data[0],
                        'old_image',
                        old_image_content)
                    return
                else:
                    self.image_converter.convert_base64_to_image(
                        track_data[5],
                        old_filename)

            if not os.path.exists(old_filename):
                os.replace(temp_filename, old_filename)
                return

            # compare temp image and new image
            # only if they are different then replace new image with temp image

            if os.getenv('USE_FILESYSTEM_TO_SAVE_IMAGES') == 'False':
                if not track_data[6] is None:
                    self.image_converter.convert_base64_to_image(
                        track_data[6],
                        new_filename)

            if os.path.exists(new_filename):
                c = ImageComparer(track_data[0], temp_filename, new_filename)
                if c.compare() > 0:
                    os.remove(new_filename)
                    os.replace(temp_filename, new_filename)

                    if os.getenv('USE_FILESYSTEM_TO_SAVE_IMAGES') == 'False':
                        new_image_content = self.\
                            image_converter.\
                            convert_image_to_base64(new_filename)
                        self._db.update_tracking(
                            track_data[0],
                            'new_image',
                            new_image_content)
            else:
                os.replace(temp_filename, new_filename)

            # compare old image and new image
            c = ImageComparer(track_data[0], old_filename, new_filename)
            if c.compare() > 0:

                logger.info("Image changed for %s\n"
                            "Sending message to %s\n",
                            track_data[3],
                            track_data[2])

                await context.bot.send_message(
                    chat_id=track_data[2],
                    text=messages["screenshot_change"] % track_data[3],
                    disable_web_page_preview=True)
                output_file_name = c.compare_and_highlight()
                await context.bot.send_message(
                        chat_id=track_data[2],
                        text="Old Image")
                await context.bot.send_photo(
                        chat_id=track_data[2],
                        photo=open(old_filename, 'rb'))
                await context.bot.send_message(
                        chat_id=track_data[2],
                        text="New Image")
                await context.bot.send_photo(
                        chat_id=track_data[2],
                        photo=open(new_filename, 'rb'))
                await context.bot.send_message(
                        chat_id=track_data[2],
                        text="Differences")
                await context.bot.send_photo(
                        chat_id=track_data[2],
                        photo=open(output_file_name, 'rb'))

                if os.path.exists(output_file_name):
                    os.remove(output_file_name)

                if os.path.exists(old_filename):
                    os.remove(old_filename)

                    if os.getenv('USE_FILESYSTEM_TO_SAVE_IMAGES') == 'False':
                        self._db.update_tracking(
                            track_data[0],
                            'old_image',
                            None)

                if os.path.exists(new_filename):
                    os.replace(new_filename, old_filename)

                    if os.getenv('USE_FILESYSTEM_TO_SAVE_IMAGES') == 'False':
                        new_image_content = \
                            self.image_converter.\
                            convert_image_to_base64(new_filename)
                        self._db.update_tracking(
                            track_data[0],
                            'old_image',
                            new_image_content)

                        self._db.update_tracking(
                            track_data[0],
                            'new_image',
                            None)
            else:
                if context.job.name.startswith('instant_'):
                    await context.bot.send_message(
                        chat_id=track_data[2],
                        text=messages["screenshot_nochange"] % track_data[3],
                        disable_web_page_preview=True)

            self._db.update_tracking(
                track_data[0],
                'last_run',
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
        except Exception as e:
            logger.error(e)

    async def call_api_once(self, context: CallbackContext):
        try:
            response = requests.get(context.job.context[3])
            if response.status_code != 200:
                logger.error("Error while calling api %s", response.text)
                await context.bot.send_message(
                    chat_id=context.job.context[2],
                    text=messages["api_error"] % context.job.context[3],
                    disable_web_page_preview=True)
                return

            soup = BeautifulSoup(response.text, 'html.parser')
            new_text = soup.prettify()
            await context.bot.send_message(
                    chat_id=context.job.context[2],
                    text=messages["api_response"] % ""
                    f"{context.job.context[3]}\n{new_text}",
                    disable_web_page_preview=True)
        except Exception as e:
            logger.error(e)
            await context.bot.send_message(
                    chat_id=context.job.context[2],
                    text=messages["api_fail"] % context.job.context[3],
                    disable_web_page_preview=True)

    async def check_api_and_compare(self, context: CallbackContext):
        try:
            response = requests.get(context.job.context[3])
            if response.status_code != 200:
                return

            soup = BeautifulSoup(response.text, 'html.parser')
            new_text = soup.prettify()
            old_text = ""

            if os.getenv('USE_FILESYSTEM_TO_SAVE_IMAGES') == 'False':
                if not context.job.context[5] is None:
                    with open(f"{os.getenv('FILESYSTEM_PATH')}"
                              f"/api_{context.job.context[0]}_old.txt",
                              "w") as f:
                        f.write(context.job.context[5])

            if os.path.exists(f"{os.getenv('FILESYSTEM_PATH')}/"
                              f"api_{context.job.context[0]}_old.txt"):
                with open(f"{os.getenv('FILESYSTEM_PATH')}/"
                          f"api_{context.job.context[0]}_old.txt", "r") as f:
                    old_text = f.read()

                if old_text != new_text:
                    await context.bot.send_message(
                        chat_id=context.job.context[2],
                        text=messages["api_change"] % context.job.context[3],
                        disable_web_page_preview=True)
                    await context.bot.send_message(
                        chat_id=context.job.context[2],
                        text=f"Old Response\n{old_text}")
                    await context.bot.send_message(
                        chat_id=context.job.context[2],
                        text=f"New Response\n{new_text}")
                    with open(f"{os.getenv('FILESYSTEM_PATH')}/"
                              f"api_{context.job.context[0]}"
                              "_old.txt", "w") as f:
                        f.write(new_text)

                    if os.getenv('USE_FILESYSTEM_TO_SAVE_IMAGES') == 'False':
                        self._db.update_tracking(
                            context.job.context[0],
                            'old_image',
                            new_text)
                else:
                    if context.job.name.startswith('instant_'):
                        await context.bot.send_message(
                         chat_id=context.job.context[2],
                         text=messages["api_nochange"] % context.job.
                         context[3],
                         disable_web_page_preview=True)
            else:
                f = open(f"{os.getenv('FILESYSTEM_PATH')}/"
                         f"api_{context.job.context[0]}_old.txt", "w")
                f.write(new_text)
                f.close()

                if os.getenv('USE_FILESYSTEM_TO_SAVE_IMAGES') == 'False':
                    self._db.update_tracking(
                        context.job.context[0],
                        'old_image',
                        new_text)
        except Exception as e:
            logger.error(e)

    async def begin_jobs(self, update: Update, context: CallbackContext):

        if str(update.effective_user.id) not in ADMIN_USERS:
            return

        urls = self._db.list_all_tracking()
        total_jobs = 0
        for url in urls:
            if context.job_queue.get_jobs_by_name(str(url[0])):
                continue

            datetime_to_run = datetime.strptime(url[7], "%Y-%m-%d %H:%M:%S")
            if url[4] == "api":
                context.job_queue.run_repeating(
                    self.check_api_and_compare,
                    timedelta(minutes=url[8]),
                    first=datetime_to_run,
                    chat_id=url[2],
                    context=url,
                    name=str(url[0]))
            elif url[4] == "screenshot":
                context.job_queue.run_repeating(
                    self.take_screenshot_and_compare,
                    timedelta(minutes=url[8]),
                    first=datetime_to_run,
                    chat_id=url[2],
                    context=url,
                    name=str(url[0]))

            details = context.job_queue.get_jobs_by_name(str(url[0]))
            logger.info(details)

            total_jobs += 1
        await self.reply_msg(update, messages["jobs_started"] % total_jobs)

    async def stop_jobs(self, update: Update, context: CallbackContext):

        if str(update.effective_user.id) not in ADMIN_USERS:
            return

        urls = self._db.list_inactive_tracking()
        total_jobs = 0
        for url in urls:
            if context.job_queue.get_jobs_by_name(str(url[0])):
                context.job_queue.stop()
                total_jobs += 1
        await self.reply_msg(update, messages["jobs_stopped"] % total_jobs)
