import urllib.request
import urllib.parse
import os
import re


def get_document_id(url):
    match = re.search(r'/document/d/([a-zA-Z0-9_-]+)', url)

    if not match:
        raise ValueError("Z URL sa nepodarilo získať ID Google dokumentu.")

    return match.group(1)


def main():
    print("========================================")
    print(" Google Docs diagnostika")
    print("========================================")
    print()

    url = input("Vlož URL Google Docs: ").strip()

    if not url:
        print("Nebola zadaná URL.")
        input("\nStlač Enter pre ukončenie...")
        return

    print()
    print("URL prijatá.")
    print("Stlač Enter a začnem sťahovať dokument...")
    input()

    try:
        document_id = get_document_id(url)

        export_url = (
            "https://docs.google.com/document/d/"
            + document_id
            + "/export?format=html"
        )

        print()
        print("Document ID:")
        print(document_id)

        print()
        print("Sťahujem:")
        print(export_url)

        request = urllib.request.Request(
            export_url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read()

            print()
            print("HTTP status:", response.status)
            print("Content-Type:", response.headers.get("Content-Type"))
            print("Veľkosť odpovede:", len(data), "bytes")

        html = data.decode("utf-8", errors="replace")

        output_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "google_doc_debug.html"
        )

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)

        print()
        print("HTML uložené do:")
        print(output_file)

        print()
        print("========== ZAČIATOK HTML ==========")
        print(html[:3000])
        print("========== KONIEC UKÁŽKY ==========")

        print()
        print("Kontrola obsahu:")

        checks = [
            "GENERAL SURVIVOR BALANCING",
            "GENERAL KILLER BALANCING",
            "TIER 5",
            "Červená",
            "Zelená",
            "podčiarknutá",
        ]

        for text in checks:
            print(
                "  %-35s %s"
                % (
                    text,
                    "ÁNO" if text in html else "NIE"
                )
            )

    except Exception as e:
        print()
        print("CHYBA:")
        print(type(e).__name__ + ":", str(e))

    print()
    input("Stlač Enter pre ukončenie...")


if __name__ == "__main__":
    main()