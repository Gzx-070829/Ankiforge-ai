"""
Note type management for AnkiForge AI.

Creates or repairs the dedicated "AnkiForge Basic" note type with fields,
template, and CSS. The CSS source of truth remains theme/style.css; v0.1.1
syncs it whenever cards are added so style tweaks do not require deleting the
note type manually.
"""

import os

from aqt import mw

NOTE_TYPE_NAME = "AnkiForge Basic"
REQUIRED_FIELDS = ["Front", "Back", "Extra", "Source", "Tags"]
TEMPLATE_NAME = "Card 1"

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
    Return the AnkiForge Basic model, creating or repairing it as needed.

    Idempotent: safe to call on every "add to Anki" action.
    """
    col = mw.col
    model = col.models.by_name(NOTE_TYPE_NAME)
    created = model is None
    if created:
        model = col.models.new(NOTE_TYPE_NAME)

    _ensure_fields(col, model)
    _ensure_template(col, model)
    model["css"] = _load_css()

    if created:
        col.models.add(model)
    else:
        _save_model(col, model)

    return model


def _ensure_fields(col, model):
    existing = {field.get("name") for field in model.get("flds", [])}
    for field_name in REQUIRED_FIELDS:
        if field_name in existing:
            continue
        new_field = col.models.new_field(field_name)
        col.models.add_field(model, new_field)
        existing.add(field_name)


def _ensure_template(col, model):
    template = None
    created_template = False
    for existing in model.get("tmpls", []):
        if existing.get("name") == TEMPLATE_NAME:
            template = existing
            break

    if template is None:
        template = col.models.new_template(TEMPLATE_NAME)
        created_template = True

    template["qfmt"] = FRONT_TEMPLATE
    template["afmt"] = BACK_TEMPLATE

    if created_template:
        col.models.add_template(model, template)


def _save_model(col, model):
    models = col.models
    if hasattr(models, "save"):
        models.save(model)
    elif hasattr(models, "update_dict"):
        models.update_dict(model)
    else:
        models.update(model)


def _load_css() -> str:
    """
    Read theme/style.css next to this package so designers can iterate on
    styling without touching Python code. Falls back to a minimal inline
    style if the file is missing for some reason.
    """
    css_path = os.path.join(os.path.dirname(__file__), "..", "theme", "style.css")
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ".card { font-family: sans-serif; font-size: 20px; }"
