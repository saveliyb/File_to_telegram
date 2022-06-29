import os
from fastapi import FastAPI, UploadFile, File
from pathlib import Path
import aiohttp

import sys
import logging
from logging import StreamHandler, Formatter, LoggerAdapter

import CONFIG

app = FastAPI()

UPLOADED_FILES_PATH = CONFIG.Config.UPLOADED_FILES_PATH

logger = logging.getLogger("logger")
logger.setLevel(logging.INFO)
handler = StreamHandler(stream=sys.stdout)
handler.setFormatter(Formatter(fmt='[%(asctime)s: %(levelname)s] %(message)s'))
logger.addHandler(handler)

logger2 = logging.getLogger('adapter')
logger2.setLevel(logging.DEBUG)
handler2 = StreamHandler(stream=sys.stdout)
handler2.setFormatter(Formatter(fmt='[%(asctime)s: %(levelname)s] %(message)s'))


class HttpErrorSendToTelegram(LoggerAdapter):
    def process(self, msg, kwargs):
        return f'{msg} http error: {self.extra["http_error"]}', kwargs


async def send_message(file: File):
    name = file.name.split("/")[-1].split("\\")[-1]
    async with aiohttp.ClientSession() as session:
        async with session.post(f'https://api.telegram.org/bot{str(CONFIG.Config.TOKEN)}/sendDocument?',
                                data={'chat_id': str(CONFIG.Config.CHAT_ID), "caption": name, "document": file}) \
                as resp:
            if resp.status == 200:
                logger.info("File send to telegram")
            else:
                adapter = HttpErrorSendToTelegram(logger2, {'http_error': str(resp.status)})
                logger2.addHandler(handler)
                adapter.error('File failed send to telegram')


async def save_file_to_uploads(file, filename):
    with open(f'{filename}', "wb") as uploaded_file:
        file_content = await file.read()
        uploaded_file.write(file_content)
        uploaded_file.close()
        logger.info("File save on server")
    return


@app.post(CONFIG.Config.URL_UPLOAD, tags=["Upload"])
async def add_event(
                    file: UploadFile = File(...)
                    ):
    file_name = os.getcwd() + f"/{UPLOADED_FILES_PATH}/" + file.filename.replace(" ", "-")
    new_filename = Path(file_name)

    await save_file_to_uploads(file, new_filename)
    with open(new_filename, "rb") as tg_file:
        await send_message(tg_file)
    os.remove(new_filename)
    return 'ok'
