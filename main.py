from fastapi import FastAPI, Request, HTTPException, status, Depends
from starlette.requests import Request
from starlette.responses import HTMLResponse
from tortoise import models
from tortoise.contrib.fastapi import register_tortoise
from models import *
from emails import *

# authentication
from authentication import *
from fastapi.security import (OAuth2PasswordBearer, OAuth2PasswordRequestForm)

# signals
from tortoise.signals import post_save
from typing import List, Optional, Type
from tortoise import BaseDBAsyncClient

# response classes
from fastapi.responses import HTMLResponse

# templates
from fastapi.templating import Jinja2Templates

# image uploads
import secrets
from fastapi import File, UploadFile
from fastapi.staticfiles import StaticFiles
from PIL import Image


app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl = "token")
env_values = dotenv_values(".env")
app.mount("/static", StaticFiles(directory = "static"), name = "static")


@app.post("/token")
async def generate_token(request_form: OAuth2PasswordRequestForm = Depends()):
    token = await token_generator(request_form.username, request_form.password)
    return {"access_token": token, "token_type": "bearer"}


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, config_credentials["JWT_SECRET"], algorithms = ["HS256"])
        user = await User.get(id = payload.get("id"))
    except:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid username or password",
            headers = {"WWW-Authenticate": "Bearer"}
        )
        
    return await user


@app.post("/user/me")
async def user_login(user: user_pydanticIn = Depends(get_current_user)):
    FILEPATH = "./static/images"
    business = await Business.get(owner = user)
    logo = business.logo
    logo_path = env_values["APP_URL"] + FILEPATH[1:] + "/" + logo
    
    return {
        "status": "ok",
        "data": {
            "usernmae": user.username,
            "email": user.email,
            "name": user.name,
            "verified": user.is_verified,
            "date_joined": user.date_joined.strftime("%b %d %Y"),
            "logo": logo_path
        }
    }


@post_save(User)
async def create_business(
    sender: "Type[User]",
    instance: User,
    created: bool,
    using_db: "Optional[BaseDBAsyncClient]",
    update_fields: List[str]
) -> None:
    if created:
        business_obj = await Business.create(
            name = instance.username, owner = instance
        )
        
        await business_pydantic.from_tortoise_orm(business_obj)
        await send_verification_email([instance.email], instance)


@app.post("/registration")
async def user_registration(user: user_pydanticIn):
    user_info = user.dict(exclude_unset = True)
    user_info["password"] = get_hashed_password(user_info["password"])
    user_obj = await User.create(**user_info)
    new_user = await user_pydantic.from_tortoise_orm(user_obj)
    return {
        "status": "ok",
        "data": f"Hello {new_user.name}! Thank you for choosing our services! Please check your e-mail inbox and click the link in the confirmation e-mail to confirm your registration."
    }


templates = Jinja2Templates(directory="templates")

@app.get("/verification", response_class = HTMLResponse)
async def email_verification(request: Request, token: str):
    user = await verify_token(token)
    
    if user and not user.is_verified:
        user.is_verified = True
        await user.save()
        return templates.TemplateResponse("verification.html", {
            "request": request, 
            "username": user.username
            })
        
    raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid or expired authorization token.",
            headers = {"WWW-Authenticate": "Bearer"}
        )


@app.get("/")
def index():
    return {"Message": "Hello World!"}


@app.post("/uploadfile/profile")
async def create_upload_file(
    file: UploadFile = File(...), 
    user: user_pydantic = Depends(get_current_user)
    ):
    FILEPATH = "./static/images"
    filename = file.filename
    extension = filename.split(".")[1]
    
    if extension not in ["png", "jpg"]:
        return {
            "status": "error",
            "detail": "File extension not allowed."
        }
        
    token_name = secrets.token_hex(10) + "." + extension
    generated_name = FILEPATH + token_name
    
    file_content = await file.read()
    
    with open(generated_name, "wb") as file:
        file.write(file_content)
        
    img = Image.open(generated_name)
    img = img.resize(size = (200, 200))
    img.save(generated_name)
    file.close()
    
    business = await Business.get(owner = user)
    owner = await business.owner
    
    if owner == user:
        business.logo = token_name
        await business.save()
    else:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Not authenticated or authorized to perform this action.",
            headers = {"WWW-Authenticate": "Bearer"}
        )
        
    file_url = env_values['APP_URL'] + generated_name[1:]
    
    return {
        "status": "ok",
        "filename": file_url,
        "message": "Profile image uploaded successfully"
    }
    
    
@app.post("/uploadfile/product/{id}")
async def create_upload_file(
    id: int, 
    file: UploadFile = File(...),
    user: user_pydantic = Depends(get_current_user)
    ):
    FILEPATH = "./static/images"
    filename = file.filename
    extension = filename.split(".")[1]
    
    if extension not in ["png", "jpg"]:
        return {
            "status": "error",
            "detail": "File extension not allowed."
        }
        
    token_name = secrets.token_hex(10) + "." + extension
    generated_name = FILEPATH + token_name
    
    file_content = await file.read()
    
    with open(generated_name, "wb") as file:
        file.write(file_content)
        
    img = Image.open(generated_name)
    img = img.resize(size = (200, 200))
    img.save(generated_name)
    file.close()
    
    product = await Product.get(id = id)
    business = await product.business
    owner = await business.owner
    
    if owner == user:
        product.image = token_name
        await product.save()
    else:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Not authenticated or authorized to perform this action.",
            headers = {"WWW-Authenticate": "Bearer"}
        )
        
    file_url = env_values['APP_URL'] + generated_name[1:]
    
    return {
        "status": "ok",
        "filename": file_url,
        "message": "Product image uploaded successfully"
    }
    

@app.post("/product")
async def add_new_product(
    product: product_pydanicIn, 
    user: user_pydantic = Depends(get_current_user)
    ):
    product = product.dict(exclude_unset = True)
    
    if product["original_price"] > 0:
        product["percentage_discount"] = ((product["original_price"] - product["new_price"]) / product["original_price"]) * 100
        product_obj = await Product.create(**product, business = user) 
        product_obj = await product_pydantic.from_tortoise_orm(product_obj)
        
        return {
            "status": "ok",
            "data": product_obj
        }
    else:
        return {
            "status": "error",
            "data": "Original price must be greater than zero"
        }
 
 
@app.get("/products")
async def get_products():
    response = await product_pydantic.from_queryset(Product.all())
    return {
        "status": "ok",
        "data": response
    }
    
    
@app.get("/products_ordered_by_date")
async def get_products():
    response = await product_pydantic.from_queryset(Product.all().order_by("-date_updated", "-date_created"))
    return {
        "status": "ok",
        "data": response
    }
    
    
@app.get("/products_ordered_by_name")
async def get_products():
    response = await product_pydantic.from_queryset(Product.all().order_by("name"))
    return {
        "status": "ok",
        "data": response
    }


@app.get("/product/{id}")
async def get_product(id: int):
    product = await Product.get(id = id)
    business = await product.business
    owner = await business.owner
    response = await product_pydantic.from_queryset_single(Product.get(id = id))
    return {
        "status": "ok",
        "data": {
            "product_details": response,
            "business_details": {
                "name": business.name,
                "city": business.city,
                "region": business.region,
                "description": business.description,
                "logo": business.logo,
                "owner_id": owner.id,
                "business_id": business.id,
                "email": owner.email,
                "date_joined": owner.date_joined.strftime("%b %d %Y")
            }
        }
    }
    

@app.get("/productbycategory/{category}")
async def get_product_by_category(category: str):
    response = await Product.get(category = category)
    return {
        "status": "ok",
        "data": response
    }


@app.delete("/product/{id}")
async def delete_product(id: int, user: user_pydantic = Depends(get_current_user)):
    product = await Product.get(id = id)
    business = await product.business
    owner = await business.owner
    
    if user == owner:
        await product.delete()
    else:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid Original Price (must be greater than zero) or Not authenticated or authorized to perform this action.",
            headers = {"WWW-Authenticate": "Bearer"}
        )
        
    return {
        "status": "ok",
        "message": "Product deleted successfully."
    }


@app.put("/product/{id}")
async def update_product(
    id: int,
    update_info: product_pydanicIn,
    user: user_pydantic = Depends(get_current_user)
    ):
    product = await Product.get(id = id)
    business = await product.business
    owner = await business.owner
    
    update_info = update_info.dict(exclude_unset = True)
    update_info["date_updated"] = datetime.utcnow()
    
    if user == owner and update_info["original_price"] > 0:
        update_info["percentage_discuont"] = ((update_info["original_price"] - update_info["new_price"]) / update_info["original_price"]) * 100
        product = await product.update_from_dict(update_info)
        await product.save()
        response = await product_pydantic.from_tortoise_orm(product)
        return {
            "status": "ok",
            "data": response
        }
    else:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Not authenticated or authorized to perform this action.",
            headers = {"WWW-Authenticate": "Bearer"}
        )


@app.put("/business/{id}")
async def update_business(id: int,
                          update_business: business_pydanticIn,
                          user: user_pydantic = Depends(get_current_user)
                          ):
    update_business = update_business.dict()
    business = await Business.get(id = id)
    business_owner = await business.owner
    
    if user == business_owner:
        await business.update_from_dict(update_business)
        await business.save()
        response = await business_pydantic.from_tortoise_orm(business)
        return {
            "status": "ok",
            "data": response
        }
    else:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Not authenticated or authorized to perform this action.",
            headers = {"WWW-Authenticate": "Bearer"}
        )
    

register_tortoise(
    app,
    db_url = "sqlite://database.sqlite",
    modules = {"models" : ["models"]},
    generate_schemas = True,
    add_exception_handlers = True
)