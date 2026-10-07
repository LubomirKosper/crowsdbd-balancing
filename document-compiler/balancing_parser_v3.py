import os
import re
import urllib.request
from html.parser import HTMLParser
from collections import OrderedDict


# ============================================================
# CONFIG
# ============================================================

RED_CLASSES = {
    "c2",
    "c67",
    "c52",
    "c36",
    "c54",
}

GREEN_CLASSES = {
    "c39",
    "c83",
}

MANDATORY_CLASSES = {
    "c60",
    "c76",
}


# ============================================================
# HTML DOM
# ============================================================

class Node:
    def __init__(self, tag=None, attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.parent = parent
        self.children = []

    def add_child(self, child):
        self.children.append(child)


class TextNode:
    def __init__(self, text, parent):
        self.text = text
        self.parent = parent


class DomParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)

        self.root = Node("root")
        self.current = self.root

        self.void_tags = {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }

    def handle_starttag(self, tag, attrs):
        node = Node(
            tag=tag.lower(),
            attrs=attrs,
            parent=self.current
        )

        self.current.add_child(node)

        if tag.lower() not in self.void_tags:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        node = Node(
            tag=tag.lower(),
            attrs=attrs,
            parent=self.current
        )

        self.current.add_child(node)

    def handle_endtag(self, tag):
        tag = tag.lower()

        node = self.current

        while node != self.root:
            if node.tag == tag:
                self.current = node.parent
                return

            node = node.parent

    def handle_data(self, data):
        if data:
            self.current.add_child(
                TextNode(
                    data,
                    self.current
                )
            )


# ============================================================
# HELPERS
# ============================================================

def get_classes(node):
    if not isinstance(node, Node):
        return set()

    value = node.attrs.get("class", "")

    return set(
        x.strip()
        for x in value.split()
        if x.strip()
    )


def get_ancestors(node):
    result = []

    current = node

    while current is not None:
        result.append(current)
        current = current.parent

    return result


def has_class_in_ancestors(node, classes):
    for ancestor in get_ancestors(node):
        if not isinstance(ancestor, Node):
            continue

        if get_classes(ancestor) & classes:
            return True

    return False


def has_class_in_ancestors_exact(node, classes):
    for ancestor in get_ancestors(node):
        if not isinstance(ancestor, Node):
            continue

        if get_classes(ancestor) & classes:
            return True

    return False


def normalize_text(text):
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_inside(node, tag_name):
    current = node.parent

    while current is not None:
        if isinstance(current, Node) and current.tag == tag_name:
            return True

        current = current.parent

    return False


def collect_text(node):
    result = []

    def walk(current):
        for child in current.children:
            if isinstance(child, TextNode):
                result.append(child.text)
            else:
                walk(child)

    walk(node)

    return normalize_text("".join(result))


def collect_text_nodes(node):
    result = []

    def walk(current):
        for child in current.children:
            if isinstance(child, TextNode):
                if normalize_text(child.text):
                    result.append(child)
            else:
                walk(child)

    walk(node)

    return result


# ============================================================
# STYLE CLASSIFICATION
# ============================================================

def classify_text_node(text_node):
    """
    Returns:
        mandatory
        allowed
        banned
        None
    """

    node = text_node.parent

    classes = set()

    current = node

    while current is not None:
        if isinstance(current, Node):
            classes.update(get_classes(current))

        current = current.parent

    if classes & MANDATORY_CLASSES:
        return "mandatory"

    if classes & GREEN_CLASSES:
        return "allowed"

    if classes & RED_CLASSES:
        return "banned"

    return None


# ============================================================
# HEADING DETECTION
# ============================================================

def normalize_heading(text):
    text = normalize_text(text)

    text = text.replace("–", "-")
    text = text.replace("—", "-")

    return text.strip()


def is_general_survivor(text):
    value = normalize_heading(text).upper()

    return value == "GENERAL SURVIVOR BALANCING"


def is_general_killer(text):
    value = normalize_heading(text).upper()

    return value == "GENERAL KILLER BALANCING"


def is_tier_heading(text):
    value = normalize_heading(text).upper()

    return re.match(
        r"^TIER\s+[0-9]+(\s*-\s*.*)?$",
        value
    ) is not None


def get_section_name(text):
    text = normalize_heading(text)

    if not text:
        return None

    upper = text.upper()

    if upper == "GENERAL SURVIVOR BALANCING":
        return "general-survivor-balancing"

    if upper == "GENERAL KILLER BALANCING":
        return "general-killer-balancing"

    match = re.match(
        r"^TIER\s+([0-9]+)\s*-\s*(.+)$",
        upper
    )

    if match:
        tier = match.group(1)
        killer = match.group(2)

        killer = re.sub(
            r"[^A-Z0-9]+",
            "-",
            killer
        )

        killer = killer.strip("-").lower()

        return "tier-%s-%s" % (
            tier,
            killer
        )

    match = re.match(
        r"^TIER\s+([0-9]+)$",
        upper
    )

    if match:
        return "tier-%s" % match.group(1)

    return None


# ============================================================
# DOCUMENT UNITS
# ============================================================

BLOCK_TAGS = {
    "p",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "td",
    "th",
}


def get_document_units(root):
    """
    Extract logical text units.

    Tables are especially important because Google Docs
    exports most of the balancing content into <td>.
    """

    units = []

    def walk(node):
        if not isinstance(node, Node):
            return

        if node.tag in BLOCK_TAGS:
            text = collect_text(node)

            if text:
                units.append(node)

            # Do not recursively add nested blocks.
            # This prevents td -> p -> span duplication.
            return

        for child in node.children:
            if isinstance(child, Node):
                walk(child)

    walk(root)

    return units


# ============================================================
# CLASSIFY UNIT
# ============================================================

def classify_unit(unit):
    """
    Returns a list of:

        (text, category)

    where category is banned/allowed/mandatory.
    """

    result = []

    text_nodes = collect_text_nodes(unit)

    for text_node in text_nodes:
        text = normalize_text(text_node.text)

        if not text:
            continue

        category = classify_text_node(text_node)

        if category is not None:
            result.append(
                (
                    text,
                    category
                )
            )

    return result


# ============================================================
# YAML
# ============================================================

def yaml_quote(value):
    value = value.replace("\\", "\\\\")
    value = value.replace('"', '\\"')
    return '"' + value + '"'


def write_yaml(data, path):
    with open(path, "w", encoding="utf-8") as f:

        f.write("# Generated from Google Docs\n")
        f.write("# Do not edit manually.\n")
        f.write("\n")

        for section_name, categories in data.items():

            f.write(
                "%s:\n" %
                section_name
            )

            for category in [
                "banned",
                "allowed",
                "mandatory"
            ]:

                values = categories.get(
                    category,
                    []
                )

                # Remove duplicates but preserve order.
                unique = []

                for value in values:
                    if value not in unique:
                        unique.append(value)

                value = ",".join(unique)

                f.write(
                    "  %s: %s\n"
                    % (
                        category,
                        yaml_quote(value)
                    )
                )

            f.write("\n")


# ============================================================
# MAIN PARSER
# ============================================================

def parse_document(html):
    parser = DomParser()
    parser.feed(html)

    units = get_document_units(
        parser.root
    )

    result = OrderedDict()

    current_section = None

    for unit in units:

        text = collect_text(unit)

        if not text:
            continue

        # ----------------------------------------------------
        # Heading?
        # ----------------------------------------------------

        section_name = get_section_name(text)

        if section_name is not None:

            current_section = section_name

            if current_section not in result:
                result[current_section] = {
                    "banned": [],
                    "allowed": [],
                    "mandatory": [],
                }

            continue

        # ----------------------------------------------------
        # Ignore anything before the first real section.
        # This includes the legend.
        # ----------------------------------------------------

        if current_section is None:
            continue

        # ----------------------------------------------------
        # Colored content
        # ----------------------------------------------------

        classified = classify_unit(unit)

        for item_text, category in classified:

            # Ignore obvious legend labels.
            if item_text.lower() in {
                "červená",
                "zelená",
                "zelená podčiarknutá",
                "red",
                "green",
                "mandatory",
                "allowed",
                "banned",
            }:
                continue

            # Google Docs can split a single name into
            # multiple text nodes. We keep the actual
            # visible text intact.
            item_text = normalize_text(item_text)

            if not item_text:
                continue

            if item_text not in result[current_section][category]:
                result[current_section][category].append(
                    item_text
                )

    return result


# ============================================================
# GOOGLE DOCS DOWNLOAD
# ============================================================

def get_document_id(url):
    match = re.search(
        r"/document/d/([a-zA-Z0-9_-]+)",
        url
    )

    if not match:
        raise ValueError(
            "Z URL sa nepodarilo získať Google Docs ID."
        )

    return match.group(1)


def download_document(url):
    document_id = get_document_id(url)

    export_url = (
        "https://docs.google.com/document/d/"
        + document_id
        + "/export?format=html"
    )

    print()
    print("Sťahujem Google Docs...")

    request = urllib.request.Request(
        export_url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        data = response.read()

    html = data.decode(
        "utf-8",
        errors="replace"
    )

    if len(html) < 1000:
        raise RuntimeError(
            "Google Docs vrátil podozrivo krátky HTML dokument."
        )

    return html


# ============================================================
# MAIN
# ============================================================

def main():

    print("========================================")
    print(" Google Docs -> YAML")
    print("========================================")
    print()

    url = input(
        "Vlož URL Google Docs: "
    ).strip()

    if not url:
        print("Nebola zadaná URL.")
        input("\nStlač Enter pre ukončenie...")
        return

    print()
    print(
        "Stlač Enter a začnem spracovanie..."
    )
    input()

    try:

        folder = os.path.dirname(
            os.path.abspath(__file__)
        )

        # ----------------------------------------------------
        # DOWNLOAD
        # ----------------------------------------------------

        html = download_document(url)

        print(
            "Stiahnuté HTML: %d bytes"
            % len(html)
        )

        # ----------------------------------------------------
        # PARSE
        # ----------------------------------------------------

        print(
            "Parsujem dokument..."
        )

        data = parse_document(html)

        # ----------------------------------------------------
        # OUTPUT
        # ----------------------------------------------------

        output_path = os.path.join(
            folder,
            "balancing_parsed.yaml"
        )

        write_yaml(
            data,
            output_path
        )

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        print()
        print("========================================")
        print(" HOTOVO")
        print("========================================")
        print()

        print(
            "Výstup:"
        )
        print(output_path)

        print()

        total = 0

        for section, categories in data.items():

            count = (
                len(categories["banned"])
                + len(categories["allowed"])
                + len(categories["mandatory"])
            )

            total += count

            print(
                "%-45s %d položiek"
                % (
                    section,
                    count
                )
            )

        print()
        print(
            "CELKOM položiek: %d"
            % total
        )

        print()

        if total == 0:
            print(
                "POZOR: YAML je prázdny."
            )
            print(
                "Dokument sa síce stiahol, ale parser"
            )
            print(
                "nenašiel farebné položky."
            )

        else:
            print(
                "YAML bol úspešne vytvorený."
            )

    except Exception as e:

        print()
        print("========================================")
        print(" CHYBA")
        print("========================================")
        print()
        print(
            type(e).__name__ + ":"
        )
        print(
            str(e)
        )

    print()
    input(
        "Stlač Enter pre ukončenie..."
    )


if __name__ == "__main__":
    main()