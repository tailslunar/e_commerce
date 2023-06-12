import random
import string
import pydantic
from tortoise import Model, fields
from pydantic import BaseModel
from datetime import datetime
from tortoise.contrib.pydantic import pydantic_model_creator


class User(Model):
    id = fields.IntField(pk = True, index = True)
    username = fields.CharField(max_length = 20, null = False, unique = True)
    email = fields.CharField(max_length = 200, null = False, unique = True)
    password = fields.CharField(max_length = 100, null = False)
    name = fields.CharField(max_length = 200, null = False)
    is_verified = fields.BooleanField(default = False)
    date_joined = fields.DatetimeField(default = datetime.utcnow)
    

class Business(Model):
    id = fields.IntField(pk = True, index = True)
    name = fields.CharField(max_length = 20, null = False, unique = True)
    city = fields.CharField(max_length = 100, mull = False, default = "Unspecified")
    region = fields.CharField(max_length = 100, null = False, default = "Unspecified")
    description = fields.TextField(null = True)
    logo = fields.CharField(max_length = 200, null = False, default = "default.jpg")
    owner = fields.ForeignKeyField("models.User", related_name = "business")
    
    
class Product(Model):
    id = fields.IntField(pk = True, index = True)
    name = fields.CharField(max_length = 100, null = False, index = True)
    sku = fields.CharField(max_length = 100, null = False, index = True, default = ''.join(random.choice(string.ascii_lowercase) for i in range(10)))
    category = fields.CharField(max_length=30, index = True)
    tags = fields.CharField(max_length = 200)
    original_price = fields.DecimalField(max_digits = 12, decimal_places=2)
    new_price = fields.DecimalField(max_digits = 12, decimal_places=2)
    percentage_discount = fields.IntField()
    offer_expiration_date = fields.DateField(default = datetime.utcnow)
    image = fields.CharField(max_length = 200, null = False, default = "productDefault.jpg")
    business = fields.ForeignKeyField("models.Business", related_name = "products")
    date_created = fields.DatetimeField(default = datetime.utcnow)
    date_updated = fields.DatetimeField(default = datetime.utcnow)
    

user_pydantic = pydantic_model_creator(User, name = "User", exclude = ("is_verified"))
user_pydanticIn = pydantic_model_creator(User, name = "UserIn", exclude_readonly = True, exclude = ("is_verified", "date_joined"))
user_pydanticOut = pydantic_model_creator(User, name = "UserOut", exclude = ("password"))

business_pydantic = pydantic_model_creator(Business, name = "Business")
business_pydanticIn = pydantic_model_creator(Business, name = "BusinessIn", exclude_readonly = True, exclude = ("logo", "id"))

product_pydantic = pydantic_model_creator(Product, name = "Product")
product_pydanicIn = pydantic_model_creator(Product, name = "ProductIn", exclude = ("percentage_discount", "id", "image", "date_created"))
