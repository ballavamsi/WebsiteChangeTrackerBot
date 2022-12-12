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
import pdb


from helpers.screenshot import Screenshot
from helpers.imagecompare import ImageComparer
from helpers.logging import logger
from helpers.db import DBHelper
from botframework.constants import *
import difflib

messages = {
    "start": "Hello %s",
    "add": "Please enter the url you want to track",
    "add_success": "Tracking %s",
    "add_fail": "Tracking failed",
    "del": "Please enter the url you want to stop tracking",
    "del_id": "Please enter the id of the url you want to stop tracking",
    "del_success": "Tracking stopped %s",
    "del_fail": "Tracking stop failed",
    "list": "Please select the url you want to track",
    "list_display": "Tracking urls",
    "list_empty": "No tracking found",
    "list_fail": "List failed",
    "screenshot": "Please enter the url you want to take screenshot",
    "screenshot_id": "Please enter the id of the url you want to take \
        screenshot",
    "screenshot_success": "Screenshot taken",
    "screenshot_fail": "Screenshot failed",
    "screenshot_change": "We have identified a change in the screenshot\
         for %s",
    "api_change": "We have identified a change in the api response for %s",
    "track_type": "Please select the type of compare from options below",
    "track_type_fail": "Invalid type",
    "invalid_url": "Invalid url",
    "invalid_type": "Invalid type",
    "invalid_id": "Invalid id",
    "reenter": "Invalid url",
    "cancel": "Cancelled",
    "blank_data": "You don't have anything in this space",
    "bye": "Bye! I hope we can talk again some day.",
    "jobs_started": "Jobs started",
}


class Actions:

    ADD, DELETE, TRACK, TRACK_TYPE, REENTER, SCREENSHOT, LIST = range(7)
    _db = DBHelper()

    def __init__(self):
        pass

    async def reply_msg(self, update: Update, *args, **kwargs):
        if kwargs.get('reply_markup') is None:
            kwargs['reply_markup'] = ReplyKeyboardRemove()

        await update.message.reply_text(*args, **kwargs)

    async def commandsHandler(self, update: Update, context: CallbackContext):
        if update.message.text in ["/cancel"]:
            await self.reply_msg(update, messages["cancel"])
            return ConversationHandler.END
        return None

    async def start(self, update: Update, context: CallbackContext):
        await self.reply_msg(update,
                             messages["start"] %
                             update.message.from_user.first_name)
        await self.reply_msg(update, messages["add"])
        return self.TRACK

    async def add_tracking_begin(self, update: Update, context):
        await self.reply_msg(update, messages["add"])
        return self.TRACK

    async def add_tracking(self, update: Update, context: CallbackContext):

        if await self.commandsHandler(update, context) is not None:
            return ConversationHandler.END

        if self._db.fetch_user(update.message.from_user.id) is None:
            self._db.insert_user(update.message.from_user.id,
                                 update.message.from_user.first_name,
                                 update.message.from_user.username)

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
        urls = self._db.list_tracking(update.message.from_user.id)
        list_urls_msg = messages["del_id"]
        for url in urls:
            list_urls_msg += f"\n{url[0]} - {url[3]} - Type: {url[4]}"
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

        # delete daata files
        if os.path.exists(f"data/screenshot_{track_data[0]}_old.png"):
            os.remove(f"data/screenshot_{track_data[0]}_old.png")
        if os.path.exists(f"data/screenshot_{track_data[0]}_new.png"):
            os.remove(f"data/screenshot_{track_data[0]}_new.png")

        self._db.delete_tracking(update.message.text)
        self.remove_job_if_exists(str(track_data[0]), context)
        await self.reply_msg(update, messages["del_success"] % track_data[3])
        return ConversationHandler.END

    async def set_tracking_type(self, update: Update,
                                context: CallbackContext):
        if await self.commandsHandler(update, context) is not None:
            return ConversationHandler.END
        context.user_data['type'] = update.message.text
        new_id = await self.add_tracking_to_db(update, context)
        track_data = self._db.fetch_tracking(new_id)

        # add jobs to queue
        if context.user_data['type'] == "api":
            context.job_queue.run_repeating(
                self.check_api_and_compare,
                DEFAULT_JOBS_RUN_TIME,
                chat_id=update.effective_message.chat_id,
                name=str(new_id),
                context=track_data)
        if context.user_data['type'] == 'screenshot':
            context.job_queue.run_repeating(
                self.take_screenshot_and_compare,
                DEFAULT_JOBS_RUN_TIME,
                chat_id=update.effective_message.chat_id,
                name=str(new_id),
                context=track_data)
        return self.LIST

    async def add_tracking_to_db(self, update, context):
        new_id = self._db.insert_tracking(
                    update.message.from_user.id,
                    update.effective_message.chat_id,
                    context.user_data['url'],
                    context.user_data['type'])
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
                urls_list = urls_list + f"{url[0]} - {url[3]} -\
                     Type: {url[4]}\n"
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
        await self.reply_msg(update, "You can enter below \
            commands\n/start - start tracking\
            \n/list - list tracking urls\
            \n/add - add tracking url\
            \n/del - delete tracking url\
            \n/help - help info\
            \n/screenshot - get screenshot of url\
            \n/cancel to cancel the current operation")

    async def screenshot_begin(self, update: Update, context: CallbackContext):
        urls = self._db.list_tracking(update.message.from_user.id)
        list_urls_msg = messages["screenshot_id"]
        for url in urls:
            list_urls_msg = list_urls_msg + f"\n{url[0]} - {url[3]} \
                - Type: {url[4]}"
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

        await self.reply_msg(update, "Taking screenshot")
        s = Screenshot(str(admin_user=track_data[2]) in ADMIN_USERS)
        filename = s.capture(track_data[3], track_data[0])
        await update.message.reply_photo(open(filename, 'rb'))
        return ConversationHandler.END

    # JOBS RELATED
    async def remove_job_if_exists(self, name: str, context: CallbackContext):
        current_jobs = context.job_queue.get_jobs_by_name(name)
        if current_jobs:
            for job in current_jobs:
                job.schedule_removal()

    async def take_screenshot_and_compare(self, context: CallbackContext):
        track_data = context.job.context
        s = Screenshot(str(admin_user=track_data[2]) in ADMIN_USERS)
        filename = s.capture(track_data[3], track_data[0])
        new_filename = f"data/screenshot_{track_data[0]}_new.png"
        old_filename = f"data/screenshot_{track_data[0]}_old.png"

        if not os.path.exists(old_filename):
            return

        if not os.path.exists(filename):
            return

        # compare temp image and new image
        # only if they are different then replace new image with temp image

        if os.path.exists(new_filename):
            c = ImageComparer(track_data[0], filename, new_filename)
            if c.compare() > 0:
                os.rename(filename, new_filename)
        else:
            os.rename(filename, new_filename)

        # compare old image and new image
        c = ImageComparer(track_data[0], old_filename, new_filename)
        if c.compare() > 0:
            await context.bot.send_message(
                chat_id=track_data[2],
                text=messages["screenshot_change"] % track_data[3],
                disable_web_page_preview=True)
            output_file_name = c.compare_and_highlight()
            await context.bot.send_message(chat_id=track_data[2],
                                           text="Old Image")
            await context.bot.send_photo(chat_id=track_data[2],
                                         photo=open(old_filename, 'rb'))
            await context.bot.send_message(chat_id=track_data[2],
                                           text="New Image")
            await context.bot.send_photo(chat_id=track_data[2],
                                         photo=open(new_filename, 'rb'))
            await context.bot.send_message(chat_id=track_data[2],
                                           text="Differences")
            await context.bot.send_photo(chat_id=track_data[2],
                                         photo=open(output_file_name, 'rb'))

            if os.path.exists(output_file_name):
                os.remove(output_file_name)

            if os.path.exists(old_filename):
                os.remove(old_filename)

            if os.path.exists(new_filename):
                os.rename(new_filename, old_filename)

    async def check_api_and_compare(self, context: CallbackContext):
        response = requests.get(context.job.context[3])
        if response.status_code != 200:
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        new_text = soup.prettify()
        old_text = ""
        if os.path.exists(f"data/api_{context.job.context[0]}_old.txt"):
            with open(f"data/api_{context.job.context[0]}_old.txt", "r") as f:
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
                with open(f"data/api_{context.job.context[0]}\
                        _old.txt", "w") as f:
                    f.write(new_text)
        else:
            f = open(f"data/api_{context.job.context[0]}_old.txt", "w")
            f.write(new_text)
            f.close()

    async def begin_jobs(self, update: Update, context: CallbackContext):

        if str(update.effective_user.id) not in ADMIN_USERS:
            return

        urls = self._db.list_all_tracking()
        for url in urls:
            if context.job_queue.get_jobs_by_name(str(url[0])):
                continue
            if url[4] == "api":
                context.job_queue.run_repeating(
                    self.check_api_and_compare,
                    DEFAULT_JOBS_RUN_TIME,
                    chat_id=url[2],
                    context=url,
                    name=str(url[0]))
            elif url[4] == "screenshot":
                context.job_queue.run_repeating(
                    self.take_screenshot_and_compare,
                    DEFAULT_JOBS_RUN_TIME,
                    chat_id=url[2],
                    context=url,
                    name=str(url[0]))
        await self.reply_msg(update, messages["jobs_started"])
