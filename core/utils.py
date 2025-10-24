import string
import random

def generate_user(name, last_name):
    digit = random.choice(string.digits)  # solo un dígito
    username = (name[0] + last_name + digit).lower()  # minúsculas
    return username

def generate_password(length=14):
    letters = string.ascii_letters
    digits = string.digits
    special_chars = "!@#$%&*/"

    all_chars = letters + digits + special_chars
    password = [
        random.choice(letters),
        random.choice(digits),
        random.choice(special_chars),
    ]
    password += random.choices(all_chars, k=length - len(password))

    random.shuffle(password)

    return ''.join(password)


