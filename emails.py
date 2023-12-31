from fastapi import (
    BackgroundTasks, 
    UploadFile, 
    File, 
    Form, 
    Depends, 
    HTTPException, 
    status
    )
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from dotenv import dotenv_values
from pydantic import BaseModel, EmailStr
from typing import List
from models import User
import jwt


config_credentials = dotenv_values(".env")

conf = ConnectionConfig(
    MAIL_USERNAME = config_credentials["EMAIL"],
    MAIL_PASSWORD = config_credentials["PASSWORD"],
    MAIL_FROM = config_credentials["EMAIL"],
    MAIL_PORT = 587,
    MAIL_SERVER = "smtp.gmail.com",
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True
)


class EmailSchema(BaseModel):
    email: List[EmailStr]
    
    
async def send_verification_email(email: List, instance: User):
    token_data = {
        "id": instance.id,
        "username": instance.username
    }
    
    token = jwt.encode(token_data, config_credentials["JWT_SECRET"], algorithm = "HS256")
    
    template = f"""
        <!DOCTYPE html>
        <html>
            <head>
            
            </head>
            <body>
                <div style = "displey: flex; aling-items: center; justify-content: center; flex-direction: column">
                    
                    <h3>Account Verification</h3>
                    <br>
                    
                    <p>Thank you for choosing our services! Plase click on the button below to verify your account:</p>
                    
                    <a style = "margin-top: 1rem; padding: 1rem; border-radius: 0.5rem; font-size: 1rem; text-decoration: none; background: #0275D8; color: white;" href="http://localhost:8000/verification/?token={token}">Verify your email</a>
                    
                    <p>Please ignore this e-mail if you didn't register for our services.</p>
                    
                </div>
            </body>
    """
    
    
    message = MessageSchema(
        subject = "Account Verification",
        recipients = email,
        body = template,
        subtype = "html"
    )
    
    fm = FastMail(conf)
    await fm.send_message(message = message)