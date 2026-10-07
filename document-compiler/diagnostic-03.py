import os
import re


def main():
    folder = os.path.dirname(os.path.abspath(__file__))
    html_file = os.path.join(folder, "google_doc_debug.html")

    if not os.path.exists(html_file):
        print("Nenašiel som google_doc_debug.html")
        input("Stlač Enter...")
        return

    with open(html_file, "r", encoding="utf-8") as f:
        html = f.read()

    print("========================================")
    print(" FARBY V GOOGLE DOCS HTML")
    print("========================================")

    for color in ["#ff0000", "#00ff00"]:
        print()
        print("########################################")
        print("FARBA:", color)
        print("########################################")

        positions = [
            m.start()
            for m in re.finditer(
                re.escape(color),
                html,
                re.IGNORECASE
            )
        ]

        print("Počet výskytov:", len(positions))

        for i, position in enumerate(positions):
            start = max(0, position - 700)
            end = min(len(html), position + 700)

            print()
            print("========== VÝSKYT %d ==========" % (i + 1))
            print(html[start:end])

    print()
    print("========================================")
    print(" CSS TRIEDY S FARBOU")
    print("========================================")

    css_pattern = re.compile(
        r'(\.[a-zA-Z0-9_-]+)\s*\{([^}]*)\}',
        re.IGNORECASE
    )

    found = []

    for match in css_pattern.finditer(html):
        class_name = match.group(1)
        css = match.group(2)

        if (
            "#ff0000" in css.lower()
            or "#00ff00" in css.lower()
            or "text-decoration" in css.lower()
        ):
            found.append(
                (
                    class_name,
                    css.strip()
                )
            )

    for class_name, css in found:
        print()
        print(class_name)
        print(css)

    print()
    print("Počet relevantných CSS tried:", len(found))

    print()
    input("Stlač Enter pre ukončenie...")


if __name__ == "__main__":
    main()