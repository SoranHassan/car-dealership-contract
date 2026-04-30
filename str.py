import os

OUTPUT_FILE = "project_structure.txt"
IGNORE_DIRS = {".git", "__pycache__", ".idea", ".vscode"}

def save_structure(root_path):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write("=== PROJECT STRUCTURE ===\n\n")

        for folder, subfolders, files in os.walk(root_path):
            # حذف پوشه‌های غیرمجاز
            subfolders[:] = [d for d in subfolders if d not in IGNORE_DIRS]

            # اگر خود فولدر git بود، رد شو
            if any(ignored in folder for ignored in IGNORE_DIRS):
                continue

            level = folder.replace(root_path, "").count(os.sep)
            indent = "    " * level
            folder_name = os.path.basename(folder) or folder

            out.write(f"{indent}[DIR] {folder_name}\n")

            for file in files:
                out.write(f"{indent}    - {file}\n")

        out.write("\n=== END OF STRUCTURE ===\n")

    print(f"\n✔ ساختار پروژه در '{OUTPUT_FILE}' ذخیره شد.\n")


if __name__ == "__main__":
    project_path = os.getcwd()
    save_structure(project_path)