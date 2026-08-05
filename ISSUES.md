# Inguitive — Open Issues

---

## Issue 1 — `Icon._replace_class`: `xlink:href` is still silently stripped after namespace regex fix

**Relates to:** TODO.md task 6, `### Improvements`, second bullet ("The namespace-cleanup regex is fragile")

**Commit that attempted the fix:** `4156cb09`

### What was supposed to be fixed

The old regex `re.sub(r'(\s)\w+:', r'\1', result)` stripped any XML namespace prefix from
attribute names, including legitimate ones like `xlink:href`. The fix narrowed the pattern to
`re.sub(r'(\s)ns\d+:', r'\1', result)` to target only auto-generated ElementTree prefixes
(`ns0:`, `ns1:`, …) and leave real prefixes like `xlink:` alone.

### Why the fix does not work

`xml.etree.ElementTree` does not preserve the original namespace prefix spellings. When it
parses an SVG containing `xlink:href`, it converts the attribute internally to Clark notation
(`{http://www.w3.org/1999/xlink}href`) and discards the `xlink:` label. When it serialises
back with `method="xml"`, it re-invents its own prefix — always `ns0:`, `ns1:`, etc. — for
every namespace it encounters, regardless of the original name.

This can be confirmed by running the pipeline directly:

```python
import xml.etree.ElementTree as ET, re

svg = '<svg xmlns:xlink="http://www.w3.org/1999/xlink"><a xlink:href="#target">Link</a></svg>'
root = ET.fromstring(svg)
root.set("class", "new-class")

result = ET.tostring(root, encoding="unicode", method="xml")
# → '<svg xmlns:ns0="http://www.w3.org/1999/xlink" class="new-class"><a ns0:href="#target">Link</a></svg>'
#   ET renamed xlink → ns0 automatically

result = re.sub(r'\s+xmlns(:\w+)?="[^"]*"', '', result)
result = re.sub(r'<ns\d+:', '<', result)
result = re.sub(r'</ns\d+:', '</', result)
result = re.sub(r'(\s)ns\d+:', r'\1', result)
# → '<svg class="new-class"><a href="#target">Link</a></svg>'
#   ns0:href stripped to href — xlink: is gone
```

The `xlink:` label never survives ET's round-trip. By the time the regex runs, the original
prefix no longer exists in the string. The new `ns\d+:` pattern strips `ns0:href` to `href`
just as the old `\w+:` pattern stripped `xlink:href` directly. The end result is identical.

`xml:space` is correctly preserved because `xml:` is a predefined XML namespace that ET
treats specially and never renames.

### Why the tests do not catch this

`test_replace_class_preserves_xlink_href` uses a substring assertion:

```python
assert 'href="#target"' in result  # ElementTree normalizes the namespace
```

`'href="#target"'` is a substring of both `xlink:href="#target"` (prefix preserved) and
`href="#target"` (prefix stripped). The assertion passes in both cases. It provides no
signal about whether the `xlink:` prefix was preserved. The test comment explicitly says
"should not be stripped to just href" but the assertion is satisfied by exactly that outcome.

### Correct fix

Register the well-known namespace prefixes with ElementTree before serialising. ET respects
registered prefixes and uses them during serialisation rather than inventing `ns0:`, `ns1:`,
etc.:

```python
import xml.etree.ElementTree as ET

ET.register_namespace("", "http://www.w3.org/2000/svg")       # default SVG namespace → no prefix
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink") # preserve xlink:
ET.register_namespace("xml", "http://www.w3.org/XML/1998/namespace")  # preserve xml:
```

With these registrations in place before `ET.tostring(...)`, the serialised output uses
`xlink:href` directly, the `ns\d+:` regexes have nothing to strip, and `xlink:href` is
preserved in the result. The `xmlns` cleanup regex still removes the `xmlns:xlink` declaration
from the root element, which is acceptable for SVG embedded in HTML5.

These registrations should be added once at module level in `components.py`, before the
`Icon` class definition, so they apply globally for the lifetime of the process.

### What also needs to change in the tests

`test_replace_class_preserves_xlink_href` must assert that the full `xlink:href` attribute
is present in the output, not just the bare `href=` fragment:

```python
assert 'xlink:href="#target"' in result   # prefix must be preserved
```

---
