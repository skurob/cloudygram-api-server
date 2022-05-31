from email.policy import HTTP
from http.client import OK
from operator import truediv
from cloudygram_api_server.models.asyncronous.user_model import *
from cloudygram_api_server.models.asyncronous.base_response import BaseResponse, BaseResponseData
from cloudygram_api_server.payload_keys import telegram_keys, download_keys, file_keys
from cloudygram_api_server.scripts.utilities import jresNoResponse
from cloudygram_api_server.telethon.telethon_wrapper import *
from cloudygram_api_server.models import UserModels
from cloudygram_api_server.scripts import jres
from pyramid_handlers import action
from pyramid.request import Request
from typing import Union
import concurrent.futures
import asyncio
import json
from fastapi import APIRouter, Response, status, UploadFile, Form, Body
from fastapi.encoders import jsonable_encoder
from telethon.tl.types import Message, MessageMediaDocument, DocumentAttributeFilename, UpdateShortMessage, PeerUser

class UserController:
    __autoexpose__ = None
    router = APIRouter()

    def __init__(self, request):
        self.request: Request = request
        self.pool = concurrent.futures.ThreadPoolExecutor()
        self.expected_errors = (TTGenericException, TTUnathorizedException, TTFileTransferException, Exception)

    @router.get("/{phonenumber}/userInfo", response_model=UserBase, response_model_exclude_unset=True)
    async def user_info_req(phonenumber: str, response: Response):
        response.headers["Content-Type"] = "application/json"
        try:
            result = await get_me(phonenumber)
            user = set_value(True, result)
        except Exception as exc:
            response.status_code = handle_exception(str(exc))
            return set_value(isSuccess=False, message=str(exc))
        return user

    @router.post("/{phonenumber}/uploadFile")
    async def upload_file_req(phonenumber: str, file: UploadFile, response: Response, mimeType: str = Form(), chatid: str = Form()):
        response.headers["Content-Type"] = "application/json"
        phone_number = phonenumber
        file_stream = file
        file_name = file.filename
        mime_type = mimeType
        chatId = chatid
        try:
            result = await upload_file(phone_number, file_name, file_stream, mime_type, chatId)
        except Exception as exc:
            response.status_code = handle_exception(str(exc))
            return BaseResponse(isSuccess=False, message=str(exc))
        result = json.loads(result)
        return result

    @router.post("/{phonenumber}/downloadFile")
    async def download_file_req(phonenumber: str, response: Response, message: str = Body(), path: str = Body()):
        response.headers["Content-Type"] = "application/json"
        try:
            phone_number = phonenumber
            message = json.loads(message)
            #Remove json attribute not need for convert to TLObject --> Message
            #del message['_']
            #del message['peer_id']['_']
            #del message['media']['_']
            #del message['media']['document']['_']
            #
            #for rows in range(len(message['media']['document']['attributes'])):
            #    del message['media']['document']['attributes'][rows]['_']
            #
            #for rows in range(len(message['media']['document']['thumbs'])):
            #    del message['media']['document']['thumbs'][rows]['_']

            message_media = Message(
                id = 			      message['id'],
                peer_id =             PeerUser(message['peer_id']),
                date =                message['date'],
                message =             message['message'],
                out =                 message['out'],
                mentioned =           message['mentioned'],
                media_unread =        message['media_unread'],
                silent =              message['silent'],
                post =                message['post'],
                from_scheduled =      message['from_scheduled'],
                legacy =              message['legacy'],
                edit_hide =           message['edit_hide'],
                pinned =              message['pinned'],
                from_id =             message['from_id'],
                fwd_from =            message['fwd_from'],
                via_bot_id =          message['via_bot_id'],
                reply_to =            message['reply_to'],
                media =               MessageMediaDocument(document = message['media']['document'], ttl_seconds = message['media']['ttl_seconds']),
                reply_markup =	      message['reply_markup'],
                entities =            message['entities'],
                views =               message['views'],
                forwards =            message['forwards'],
                replies =             message['replies'],
                edit_date =           message['edit_date'],
                post_author =         message['post_author'],
                grouped_id =          message['grouped_id'],
                restriction_reason =  message['restriction_reason'],
                ttl_period =          message['ttl_period']      
            )
            result: BaseResponse = await download_file(phone_number, message_media, message['peer_id']['user_id'], file_path=path)
            if (result.isSuccess == False):
                raise ValueError(result.message)

        except Exception as exc:
            response.status_code = handle_exception(str(exc))
            return BaseResponse(isSuccess=False, message=str(exc))
        return result

    @router.get("/{phonenumber}/isAuthorized")
    async def is_authorized_req(phonenumber: str, response: Response):
        response.headers["Content-Type"] = "application/json"
        try:
            result = await is_authorized(phonenumber)
        except Exception as exc:
            response.status_code = handle_exception(str(exc))
            return BaseResponse(isSuccess=False, message=str(exc))
        if (result):
            response = BaseResponse(isSuccess=True, message="User is authorizated")
        else:
            response = BaseResponse(isSuccess=False, message="User is NOT authorizated")
        return response

    @router.get("/{phonenumber}/downloadProfilePhoto")
    async def download_profile_photo_req(phonenumber: str, response: Response, path: str = None, filename: str = None):
        response.headers["Content-Type"] = "application/json"
        try:
            result = await download_profile_photo(phonenumber, path, filename)
        except Exception as exc:
            response.status_code = handle_exception(str(exc))
            return BaseResponse(isSuccess=False, message=str(exc))

        if result == False:
            response = BaseResponse(isSuccess=False, message="User has no profile photo")
        else:
            response = BaseResponseData(isSuccess=True, message="Profile photo downloaded", data=result)  # path where the picture got downloaded
        return response

    @action(name="contacts", renderer="json", request_method="GET")
    def contacts_req(self):
        phone_number = self.request.matchdict[telegram_keys.phone_number][1:]
        try:
            result = self.pool.submit(
                asyncio.run,
                get_contacts(phone_number)
            ).result()
        except self.expected_errors as exc:
            return self.handle_exceptions(exc)
        response = UserModels.success(
            message="Contacts fetched.",
            data=result
        )
        return jres(response, 200)

    @action(name="logout", renderer="json", request_method="DELETE")
    def logout_req(self):
        phone_number = self.request.matchdict[telegram_keys.phone_number][1:]
        try:
            result = self.pool.submit(
                asyncio.run,
                logout(phone_number)
            ).result()
        except self.expected_errors as exc:
            return self.handle_exceptions(exc)
        if not result:
            return jres(UserModels.failure(message="Clouldn't log out"), 200)
        response = UserModels.success(
            message="Log out successful.",
            data=result
        )
        return jres(response, 200)

    @action(name="sessionValid", renderer="json", request_method="GET")
    def session_valid_req(self):
        phone_number = self.request.matchdict[telegram_keys.phone_number][1:]
        try:
            result = self.pool.submit(
                asyncio.run,
                session_valid(phone_number)
            ).result()
        except self.expected_errors as exc:
            return self.handle_exceptions(exc)
        if result:
            response = UserModels.success(
                message="Session is still valid."
            )
        else:
            response = UserModels.failure(
                message="Session is not valid."
            )
        return jres(response, 200)

    @action(name="uploadFilePath", renderer="json", request_method="POST")
    def upload_file_path(self):
        phone_number = self.request.matchdict[telegram_keys.phone_number][1:]
        file_stream = self.request.POST[file_keys.path]
        file_name = self.request.POST[file_keys.filename]
        mime_type = self.request.POST[file_keys.mime_type]
        try:
            result = self.pool.submit(
                asyncio.run,
                upload_file_path(phone_number, file_name, file_stream, mime_type)
            ).result()
        except self.expected_errors as exc:
            return self.handle_exceptions(exc)
        return jres(result, 200)

    @action(name="dialogs", renderer="json", request_method="GET")
    def contacts_req(self):
        phone_number = self.request.matchdict[telegram_keys.phone_number][1:]
        try:
            result = self.pool.submit(
                asyncio.run,
                get_dialog(phone_number)
            ).result()
        except self.expected_errors as exc:
            return self.handle_exceptions(exc)
        response = UserModels.success(
            message="Ok",
            data=result
        )
        return result

def handle_exceptions(exception: Union[TTGenericException, TTUnathorizedException, TTFileTransferException, Exception]) -> dict:
        if type(exception) is TTGenericException or type(exception) is Exception or type(exception) is TTFileTransferException:
            return jres(UserModels.failure(str(exception)), status=500)
        elif type(exception) is TTUnathorizedException:
            return jres(UserModels.failure(str(exception)), status=401)
        else:
            return jres(UserModels.failure(str(exception)), status=500)

def handle_exception(exception: Union[TTGenericException, TTUnathorizedException, TTFileTransferException, Exception]) -> status:
        if type(exception) is TTGenericException or type(exception) is Exception or type(exception) is TTFileTransferException:
            return status.HTTP_500_INTERNAL_SERVER_ERROR
        elif type(exception) is TTUnathorizedException:
            return status.HTTP_401_UNAUTHORIZED
        else:
            return status.HTTP_500_INTERNAL_SERVER_ERROR