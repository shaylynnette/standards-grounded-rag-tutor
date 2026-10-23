"""Command line: python -m tutor.cli "fifth grade rounding decimals" """
import sys

from .answer import ask


def main() -> None:
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        print('Usage: python -m tutor.cli "your question about K-5 Texas standards"')
        raise SystemExit(2)
    r = ask(question)
    print(r.answer)
    if r.answered:
        print("\nSource: https://tea.texas.gov/academics/curriculum-standards/teks-review/texas-essential-knowledge-and-skills")


if __name__ == "__main__":
    main()
