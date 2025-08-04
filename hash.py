import bcrypt

# List of passwords
passwords = [
    "3`3cyjP+v-5f{2D",
    "TbNH(=pw293[S}}"
]

print(passwords)

# Function to hash passwords
def hash_passwords(password_list):
    hashed_passwords = {}
    for idx, password in enumerate(password_list):
        # Generate a salt and hash the password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        hashed_passwords[f"Emp ID {101 + idx}"] = hashed.decode('utf-8')
    return hashed_passwords

# Hash the passwords and print them
hashed_passwords = hash_passwords(passwords)
for passwords, hashed in hashed_passwords.items():
    print(f"{passwords}: {hashed}")
