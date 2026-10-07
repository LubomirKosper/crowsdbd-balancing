import os
import re
from html.parser import HTMLParser


class StyleParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)

        self.current_classes = []
        self.current_style = {}
        self.current_text = []

        self.results = []

        self.in_style = False
        self.style_content = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "style":
            self.in_style = True
            self.style_content = []
            return

        classes = attrs.get("class", "")
        style = attrs.get("style", "")

        self.current_classes.append(classes)
        self.current_style = self.parse_inline_style(style)

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False
            return

        if self.current_classes:
            self.current_classes.pop()

    def handle_data(self, data):
        if self.in_style:
            self.style_content.append(data)
            return

        text = data.strip()

        if not text:
            return

        classes = self.current_classes[-1] if self.current_classes else ""
        style = self.current_style

        self.results.append(
            {
                "text": text,
                "classes": classes,
                "style": style,
            }
        )

    def parse_inline_style(self, style):
        result = {}

        for part in style.split(";"):
            if ":" not in part:
                continue

            key, value = part.split(":", 1)

            result[key.strip().lower()] = value.strip().lower()

        return result


def normalize_color(value):
    if not value:
        return None

    value = value.lower().replace(" ", "")

    # #ff0000
    match = re.match(r"^#([0-9a-f]{6})$", value)

    if match:
        return match.group(1)

    # rgb(255,0,0)
    match = re.match(
        r"^rgb\((\d+),(\d+),(\d+)\)$",
        value
    )

    if match:
        r = int(match.group(1))
        g = int(match.group(2))
        b = int(match.group(3))

        return "%02x%02x%02x" % (r, g, b)

    return value


def main():
    folder = os.path.dirname(os.path.abspath(__file__))
    html_file = os.path.join(folder, "google_doc_debug.html")

    if not os.path.exists(html_file):
        print("Nenašiel som:")
        print(html_file)
        print()
        input("Stlač Enter pre ukončenie...")
        return

    print("Načítavam:")
    print(html_file)
    print()

    with open(html_file, "r", encoding="utf-8") as f:
        html = f.read()

    parser = StyleParser()
    parser.feed(html)

    print("TEXTOVÉ PRVKY:")
    print("========================================")

    count = 0

    for item in parser.results:

        text = item["text"]
        classes = item["classes"]
        style = item["style"]

        # Zaujímajú nás najmä krátke texty
        # ktoré vyzerajú ako názvy perk/itemov.
        if len(text) > 150:
            continue

        print()
        print("TEXT:")
        print(repr(text))

        print("CLASS:")
        print(repr(classes))

        print("STYLE:")
        print(repr(style))

        count += 1

        if count >= 100:
            break

    print()
    print("========================================")
    print("Počet nájdených textových fragmentov:", len(parser.results))
    print("Zobrazených prvých:", count)

    print()
    print("========================================")
    print("HĽADANIE FARIEB V CELKOM HTML")
    print("========================================")

    colors = re.findall(
        r"#[0-9a-fA-F]{6}",
        html
    )

    unique_colors = sorted(set(
        c.lower()
        for c in colors
    ))

    for color in unique_colors:
        occurrences = html.lower().count(color)

        if occurrences >= 2:
            print(
                "%s -> %d výskytov"
                % (color, occurrences)
            )

    print()
    print("========================================")
    print("HĽADANIE UNDERLINE")
    print("========================================")

    underline_matches = re.findall(
        r"[^{}]*text-decoration[^{}]*",
        html,
        re.IGNORECASE
    )

    for match in underline_matches[:30]:
        print(match.strip())

    print()
    input("Stlač Enter pre ukončenie...")


if __name__ == "__main__":
    main()