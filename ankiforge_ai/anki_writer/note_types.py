"""
Note type management for AnkiForge AI.

Creates a dedicated "AnkiForge Basic" note type the first time it's needed,
with fields: Front, Back, Extra, Source, Tags. Also installs a beautified
card template + CSS (this is the "card appearance" piece of the project --
see theme/style.css for the source of truth on styling, kept in sync here).

Uses the modern Anki collection API (col.models.new_field / add_field /
new_template / add_template), which targets Anki 2.1.50+.
"""

from aqt import mw

NOTE_TYPE_NAME = "AnkiForge Basic"

FRONT_TEMPLATE = """<div class="card-inner">
  <div class="front">{{Front}}</div>
</div>"""

BACK_TEMPLATE = """<div class="card-inner">
  <div class="front">{{Front}}</div>
  <hr id="answer">
  <div class="back">{{Back}}</div>
  {{#Extra}}<div class="extra">{{Extra}}</div>{{/Extra}}
  {{#Source}}<div class="source">来源：{{Source}}</div>{{/Source}}
</div>"""


def ensure_note_type():
    """
    Return the AnkiForge Basic model, creating it (with fields + template +
    CSS) the first time it's called. Idempotent: safe to call on every
    "add to Anki" action.
    """
    col = mw.col
    model = col.models.by_name(NOTE_TYPE_NAME)
    if model is not None:
        return model

    model = col.models.new(NOTE_TYPE_NAME)

    for field_name in ["Front", "Back", "Extra", "Source", "Tags"]:
        new_field = col.models.new_field(field_name)
        col.models.add_field(model, new_field)

    template = col.models.new_template("Card 1")
    template["qfmt"] = FRONT_TEMPLATE
    template["afmt"] = BACK_TEMPLATE
    col.models.add_template(model, template)

    model["css"] = _load_css()

    col.models.add(model)
    return model


def _load_css() -> str:
    """
    Read theme/style.css next to this package so designers can iterate on
    styling without touching Python code. Falls back to a minimal inline
    style if the file is missing for some reason.
    """
    import os

    css_path = os.path.join(os.path.dirname(__file__), "..", "theme", "style.css")
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ".card { font-family: sans-serif; font-size: 20px; }"
