from pathlib import Path

def main():
    root = Path.cwd()
    for path in sorted(root.rglob("*")):
        if ".git" in path.parts:
            continue
        print(path.relative_to(root))

if __name__ == "__main__":
    main()
