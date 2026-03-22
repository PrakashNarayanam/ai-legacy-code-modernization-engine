from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env in this folder before importing modules that depend on them
load_dotenv(Path(__file__).with_name(".env"))

from chunker import chunk_code
from modernizer import modernize_chunk


def read_legacy_code(file_path):
    with open(file_path, "r") as f:
        return f.read()

def write_modern_code(code):
    with open("modernized_code.java", "w") as f:
        f.write(code)

def main():

    print("Reading legacy code...")

    code = read_legacy_code("legacy_code_sample.java")

    print("Chunking code...")
    chunks = chunk_code(code)

    modern_code = ""

    for i, chunk in enumerate(chunks):
        print(f"Modernizing chunk {i+1}...")
        modern_chunk = modernize_chunk(chunk)
        modern_code += modern_chunk + "\n"

    write_modern_code(modern_code)

    print("Modernized code saved as modernized_code.java")


if __name__ == "__main__":
    main()