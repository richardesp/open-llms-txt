# src/open_llms_txt/main.py

import argparse

def cli():
    parser = argparse.ArgumentParser(prog="llms-gen", description="Generate llms.txt and .html.md files for LLM access.")
    subparsers = parser.add_subparsers(dest="command")

    generate_parser = subparsers.add_parser("generate", help="Generate llms.txt")
    generate_parser.add_argument("--url", help="Website URL or path to docs")

    convert_parser = subparsers.add_parser("convert", help="Convert .html to .html.md")
    convert_parser.add_argument("--input", help="Path to .html file")

    args = parser.parse_args()

    if args.command == "generate":
        print(f"✅ Generating llms.txt from: {args.url}")
    elif args.command == "convert":
        print(f"📄 Converting {args.input} to .html.md")
    else:
        parser.print_help()
