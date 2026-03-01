# Patent Category Keyword Rules

Used by `compile_patents.py` to auto-categorize patents by title.
Rules are checked in order; first match wins.

| Category | Keywords / Regex |
|----------|-----------------|
| Slicing | slic, slicing, knife, knives, blade, cutter unit, caliber |
| Thermoforming | thermoform, deep draw, deep-draw, forming station |
| Tray Sealer | tray seal, tray sealer, tray-seal |
| Chamber Machine | chamber, vacuum bag, bag seal, bulk goods in bag |
| Sealing | seal / sealing (excluding tray/chamber context) |
| Cutting | cutting station, complete-cut, punching device |
| Automation/Robot | robot, picker, gripper, pick-and-place, loading station |
| Conveying | convey, transport, transfer, lane divider, race track |
| Smart/Digital | process param, bus node, digital, smart, predictive, recipe |
| High-pressure | high-pressure, HPP |
| Sustainable | paper material, cardboard, fiber-containing, reclosable |
| Shrink | shrink |
| Auxiliary | winder, nozzle, suction, mandrel, mounting plate, valve |
| Packaging | reclosable package, liquid package, package design |
| Other | (fallback) |

## Extending Categories

To add a new category, edit `compile_patents.py`:
```python
CATEGORY_RULES = [
    ("My New Category", r"keyword1|keyword2|phrase"),
    ...  # existing rules
]
```
Rules use Python `re.search()` on lowercase title; order matters.
