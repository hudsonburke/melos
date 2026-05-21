"""MJCF default class resolver for ``melos.sim.mujoco.importers``."""

from __future__ import annotations

from xml.etree.ElementTree import Element

DefaultClassMap = dict[str, dict[str, dict[str, str]]]


def resolve_defaults(root: Element) -> DefaultClassMap:
    dmap: DefaultClassMap = {}
    default_section = root.find("default")
    if default_section is None:
        return dmap
    _parse_default_element(default_section, parent_attrs={}, dmap=dmap)
    return dmap


def _parse_default_element(
    element: Element,
    parent_attrs: dict[str, dict[str, str]],
    dmap: DefaultClassMap,
) -> None:
    class_name = element.get("class")
    if class_name is not None:
        class_attrs: dict[str, dict[str, str]] = {}
        for tag, attrs in parent_attrs.items():
            class_attrs[tag] = dict(attrs)
        for child in element:
            if child.tag == "default":
                continue
            tag = child.tag
            own_attrs = dict(child.attrib)
            if tag not in class_attrs:
                class_attrs[tag] = {}
            class_attrs[tag].update(own_attrs)
        dmap[class_name] = class_attrs
        for child in element:
            if child.tag == "default":
                _parse_default_element(child, parent_attrs=class_attrs, dmap=dmap)
    else:
        for child in element:
            if child.tag == "default":
                _parse_default_element(child, parent_attrs=parent_attrs, dmap=dmap)


def apply_defaults(
    element: Element,
    class_name: str | None,
    defaults: DefaultClassMap,
) -> None:
    if class_name is None or class_name not in defaults:
        return
    class_attrs = defaults[class_name]
    tag_attrs = class_attrs.get(element.tag, {})
    for attr_name, attr_value in tag_attrs.items():
        if element.get(attr_name) is None:
            element.set(attr_name, attr_value)


def get_active_class(element: Element, parent_class: str | None) -> str | None:
    own_class = element.get("class")
    if own_class is not None:
        return own_class
    return parent_class
