import subprocess
import os
from getpass import getpass

MASTER_KEY = "@Soran9978"  

LICENSE_PATH = r"C:\ProgramData\AutoGarideh"
LICENSE_FILE = os.path.join(LICENSE_PATH, "license.key")


def get_system_uuid():
    try:
        output = subprocess.check_output("wmic csproduct get uuid", shell=True)
        uuid = output.decode().split("\n")[1].strip()
        return uuid
    except:
        return None


def save_license(uuid):
    os.makedirs(LICENSE_PATH, exist_ok=True)
    with open(LICENSE_FILE, "w") as f:
        f.write(uuid)


def check_license():
    if not os.path.exists(LICENSE_FILE):
        return False

    try:
        with open(LICENSE_FILE, "r") as f:
            saved_uuid = f.read().strip()

        current_uuid = get_system_uuid()
        return saved_uuid == current_uuid
    except:
        return False


def license_check():
    if check_license():
        return True

    print("🔒 نرم‌افزار قفل است.")
    key = getpass("رمز: ").strip()

    if key == MASTER_KEY:
        uuid = get_system_uuid()
        save_license(uuid)
        print("✔ فعال‌سازی موفقیت‌آمیز بود.")
        return True
    else:
        print("❌ رمز اشتباه است.")
        return False