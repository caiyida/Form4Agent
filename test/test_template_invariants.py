"""Regression tests for the layout-critical XML in the Form4 Word template."""

from collections import Counter
from hashlib import sha256
from pathlib import Path, PurePosixPath
import sys
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from lxml import etree


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = PROJECT_ROOT / "templates" / "Form4_Template.docx"
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from form4_engine import fill_form  # noqa: E402


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
}

EXPECTED_ANCHOR_HASHES = {
    ("initials", "9"): "b2690cca5e8c9908ea290035fc7e1f3dc8803bedfe5f368969a8d164684c5d16",
    ("initials", "10"): "72b26dbdff828b11d7f71da52c6046baccf9623a23d636593bd14c2d82a2b420",
    ("initials", "11"): "315cb30bb9a09cf69b335b960724ca5b821302b353a41dfc59ccbe602962d1d7",
    ("initials", "12"): "1dc61be0c64fd4e3fc8b97fab74a2419c767ff29b9ea487aafa60a7c4df34cea",
    ("initials", "13"): "8f9d9fc7d50ee4925923e047fb4d1b1df13b99e6e4e9a56f8a4843833aa1abc8",
    ("initials", "14"): "3c07bc380f8072bcee3ad529c6b76b125079013875c024a98f73b4580f8948bb",
    ("initials", "15"): "dcd6ddbab0e51e50e94d67ea262c967c72b9aaf8f6800ad9a78c6ad385c8a2d4",
    ("signature", "16"): "b725ba3708ca0b4f1ed1ec92fe76373459f0e129cf01cc7b7a62252118068448",
}

EXPECTED_POSITIONS = {
    ("initials", "9"): ("column", "5751830", "page", "631825", "486410", "234950"),
    ("initials", "10"): ("column", "5749925", "page", "625475", "486410", "234950"),
    ("initials", "11"): ("column", "5815965", "page", "599440", "486410", "234950"),
    ("initials", "12"): ("column", "5768340", "page", "610235", "486410", "234950"),
    ("initials", "13"): ("column", "5787390", "page", "614045", "486410", "234950"),
    ("initials", "14"): ("column", "5770245", "page", "605790", "486410", "234950"),
    ("initials", "15"): ("column", "5788660", "page", "595630", "486410", "234950"),
    ("signature", "16"): ("column", "1674495", "page", "26035", "1119505", "428625"),
}

EXPECTED_IMAGE_RELATIONSHIPS = {
    ("initials", "9"): ("rId8", "media/image2.jpeg", "545fd36660d10fb2e74074ba28cbee698c9b4ed839b4ee920e153994391dc95f"),
    ("initials", "10"): ("rId8", "media/image2.jpeg", "545fd36660d10fb2e74074ba28cbee698c9b4ed839b4ee920e153994391dc95f"),
    ("initials", "11"): ("rId8", "media/image2.jpeg", "545fd36660d10fb2e74074ba28cbee698c9b4ed839b4ee920e153994391dc95f"),
    ("initials", "12"): ("rId8", "media/image2.jpeg", "545fd36660d10fb2e74074ba28cbee698c9b4ed839b4ee920e153994391dc95f"),
    ("initials", "13"): ("rId8", "media/image2.jpeg", "545fd36660d10fb2e74074ba28cbee698c9b4ed839b4ee920e153994391dc95f"),
    ("initials", "14"): ("rId8", "media/image2.jpeg", "545fd36660d10fb2e74074ba28cbee698c9b4ed839b4ee920e153994391dc95f"),
    ("initials", "15"): ("rId8", "media/image2.jpeg", "545fd36660d10fb2e74074ba28cbee698c9b4ed839b4ee920e153994391dc95f"),
    ("signature", "16"): ("rId9", "media/image3.jpeg", "cf663797e5778d2fb169d7c63015a9e6c8aa7601bc4718b2c63885ad1e44657e"),
}

EXPECTED_SECTION_HASHES = [
    "664c9c41d43695f9edea5408559681ffd13496080c0dc7022dbf8e5d4f025e53",
    "a23c853450de1bad4b93b43dc10ede94db2b1b8b028fe50ec721f064203d3b89",
]

EXPECTED_TABLES = [
    ("c2e1c716c063da4e6e960e6894e7a95a20a4e98b4e95c5a7fe544fd183a4c368", [4, 2, 4, 2, 4, 2, 4, 2, 4, 2]),
    ("d136d845ade1bc133389025f1b34a7c3e6cf2bdfc4ba9f02d71cc6d8a98deb7b", [1, 1, 4, 4, 4, 1, 1, 4, 4, 4, 1, 1, 4, 4, 4, 1, 1, 4, 4, 4]),
]

EXPECTED_PLACEHOLDERS = Counter(
    {
        "agreement_date": 6,
        "tenant1_name": 1,
        "tenant1_nric": 1,
        "tenant2_name": 1,
        "tenant2_nric": 1,
        "tenant3_name": 1,
        "tenant3_nric": 1,
        "tenant4_name": 1,
        "tenant4_nric": 1,
        "property_address": 1,
        "lease_term": 1,
        "commission_term": 1,
        "renew_commission": 1,
        "additional_term": 1,
    }
)


def canonical_hash(element):
    xml = etree.tostring(element, method="c14n", exclusive=True)
    return sha256(xml).hexdigest()


def single_text(element, xpath):
    values = element.xpath(xpath, namespaces=NS)
    if len(values) != 1:
        raise AssertionError(f"Expected one value for {xpath}, found {len(values)}")
    return values[0]


def inspect_docx(path):
    with ZipFile(path) as archive:
        document = etree.fromstring(archive.read("word/document.xml"))
        relationships_xml = etree.fromstring(
            archive.read("word/_rels/document.xml.rels")
        )
        relationships = {
            relationship.get("Id"): relationship.get("Target")
            for relationship in relationships_xml
        }

        anchor_hashes = {}
        positions = {}
        image_relationships = {}
        anchors = document.xpath(
            '//wp:anchor[wp:docPr[@descr="signature" or @descr="initials"]]',
            namespaces=NS,
        )
        for anchor in anchors:
            doc_properties = anchor.find("wp:docPr", NS)
            key = (doc_properties.get("descr"), doc_properties.get("id"))
            anchor_hashes[key] = canonical_hash(anchor)
            positions[key] = (
                single_text(anchor, "./wp:positionH/@relativeFrom"),
                single_text(anchor, "./wp:positionH/wp:posOffset/text()"),
                single_text(anchor, "./wp:positionV/@relativeFrom"),
                single_text(anchor, "./wp:positionV/wp:posOffset/text()"),
                single_text(anchor, "./wp:extent/@cx"),
                single_text(anchor, "./wp:extent/@cy"),
            )

            relationship_id = single_text(anchor, ".//a:blip/@r:embed")
            target = relationships[relationship_id]
            image_part = str(PurePosixPath("word") / target)
            image_relationships[key] = (
                relationship_id,
                target,
                sha256(archive.read(image_part)).hexdigest(),
            )

        section_hashes = [
            canonical_hash(section)
            for section in document.xpath("//w:sectPr", namespaces=NS)
        ]

        tables = []
        for table in document.xpath("//w:tbl", namespaces=NS):
            geometry = etree.Element("geometry")
            geometry_nodes = table.xpath(
                "./w:tblPr|./w:tblGrid|./w:tr/w:trPr|./w:tr/w:tc/w:tcPr",
                namespaces=NS,
            )
            for node in geometry_nodes:
                geometry.append(etree.fromstring(etree.tostring(node)))
            cells_per_row = [
                len(row.xpath("./w:tc", namespaces=NS))
                for row in table.xpath("./w:tr", namespaces=NS)
            ]
            tables.append((canonical_hash(geometry), cells_per_row))

        placeholder_counts = Counter()
        for text in document.xpath("//w:t/text()", namespaces=NS):
            if text.startswith("{{") and text.endswith("}}"):
                placeholder_counts[text[2:-2]] += 1

        return {
            "anchor_hashes": anchor_hashes,
            "positions": positions,
            "image_relationships": image_relationships,
            "section_hashes": section_hashes,
            "tables": tables,
            "placeholder_counts": placeholder_counts,
        }


class TemplateInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = inspect_docx(TEMPLATE_PATH)

    def test_signature_and_initial_anchor_xml(self):
        self.assertEqual(self.template["anchor_hashes"], EXPECTED_ANCHOR_HASHES)

    def test_signature_and_initial_positions(self):
        self.assertEqual(self.template["positions"], EXPECTED_POSITIONS)

    def test_signature_and_initial_image_relationships(self):
        self.assertEqual(
            self.template["image_relationships"], EXPECTED_IMAGE_RELATIONSHIPS
        )

    def test_section_and_page_properties(self):
        self.assertEqual(self.template["section_hashes"], EXPECTED_SECTION_HASHES)

    def test_table_structure_and_geometry(self):
        self.assertEqual(self.template["tables"], EXPECTED_TABLES)

    def test_expected_placeholders(self):
        self.assertEqual(
            self.template["placeholder_counts"], EXPECTED_PLACEHOLDERS
        )

    def test_generation_preserves_signature_and_initial_anchors(self):
        form_data = {
            key: "" if key == "additional_term" else f"TEST_{key}"
            for key in EXPECTED_PLACEHOLDERS
        }

        with TemporaryDirectory() as temp_dir:
            generated_path = Path(temp_dir) / "generated.docx"
            fill_form(form_data, generated_path)
            generated = inspect_docx(generated_path)

        self.assertEqual(
            set(generated["anchor_hashes"]),
            set(self.template["anchor_hashes"]),
            "Generation added or removed a signature/initial drawing anchor",
        )
        self.assertEqual(generated["anchor_hashes"], self.template["anchor_hashes"])
        self.assertEqual(generated["positions"], self.template["positions"])
        self.assertEqual(
            generated["image_relationships"], self.template["image_relationships"]
        )

    def test_fixed_business_choices_remain_selected(self):
        with ZipFile(TEMPLATE_PATH) as archive:
            document = etree.fromstring(archive.read("word/document.xml"))

        for text in ("exclusive", "shall not", "has", "does not authorise"):
            runs = document.xpath(
                '//w:r[w:t[text()=$text] and w:rPr/w:strike]',
                namespaces=NS,
                text=text,
            )
            self.assertEqual(len(runs), 1, f"Expected {text!r} to remain struck out")

        selected = document.xpath(
            '//w:checkBox[w:default[@w:val="1"] and w:checked[not(@w:val)]]',
            namespaces=NS,
        )
        unselected = document.xpath(
            '//w:checkBox[w:default[@w:val="0"] and w:checked[@w:val="0"]]',
            namespaces=NS,
        )
        self.assertEqual(len(selected), 1, "Expected GST Yes to remain checked")
        self.assertEqual(len(unselected), 1, "Expected GST No to remain unchecked")


if __name__ == "__main__":
    unittest.main()
