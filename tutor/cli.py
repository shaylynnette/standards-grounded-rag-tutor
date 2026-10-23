"""Command line: python -m tutor.cli "fifth grade rounding decimals" """
import sys

from .answer import ask


def main() -> None:
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        print('Usage: python -m tutor.cli "your question about K-5 Texas math standards"')
        raise SystemExit(2)
    r = ask(question)
    print(r.answer)
    if r.answered:
        print("\nSource: https://tea.texas.gov/laws-and-rules/texas-administrative-code/19-tac-chapter-111")


if __name__ == "__main__":
    main()
