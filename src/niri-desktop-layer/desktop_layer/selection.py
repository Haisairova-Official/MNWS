"""Selection geometry and collision-free group movement without GTK or I/O."""

from __future__ import annotations


def move_group(
    layout: dict[str, tuple[int, int] | list[int]],
    selected: set[str],
    dx: int,
    dy: int,
    columns: int,
    rows: int,
) -> dict[str, tuple[int, int]]:
    """Translate selected grid cells together, relocating destination occupants.

    The caller supplies a valid, collision-free layout, such as arrange_grid's
    result. Unknown selected keys are ignored. Clamp the requested delta against
    the whole selection, so its shape cannot change at a desktop edge. Only
    unselected entries under the destination cells move: they prefer the nearest
    vacated source cell, then any other free cell. Manhattan distance and
    column/row/key ordering make displacement independent of dictionary order.

    Return a tuple-valued snapshot, never modifying the input. No-op drags and
    invalid dimensions retain every original position. An invalid input layout
    is also retained rather than risking lost entries while trying to repair it.
    """
    positions = {key: tuple(cell) for key, cell in layout.items()}
    if (
        type(columns) is not int
        or type(rows) is not int
        or columns <= 0
        or rows <= 0
        or type(dx) is not int
        or type(dy) is not int
    ):
        return positions
    if any(
        len(cell) != 2
        or any(type(value) is not int for value in cell)
        or not (0 <= cell[0] < columns and 0 <= cell[1] < rows)
        for cell in positions.values()
    ) or len(set(positions.values())) != len(positions):
        return positions

    moving = set(positions).intersection(selected)
    if not moving:
        return positions
    source_cells = {positions[key] for key in moving}
    dx = max(-min(cell[0] for cell in source_cells), min(dx, columns - 1 - max(cell[0] for cell in source_cells)))
    dy = max(-min(cell[1] for cell in source_cells), min(dy, rows - 1 - max(cell[1] for cell in source_cells)))
    if dx == 0 and dy == 0:
        return positions

    destinations = {key: (positions[key][0] + dx, positions[key][1] + dy) for key in moving}
    destination_cells = set(destinations.values())
    displaced = sorted(
        (key for key, cell in positions.items() if key not in moving and cell in destination_cells),
        key=lambda key: (*positions[key], key),
    )
    displaced_keys = set(displaced)
    occupied = destination_cells | {
        cell for key, cell in positions.items() if key not in moving and key not in displaced_keys
    }
    vacated = source_cells - occupied
    result = positions.copy()
    result.update(destinations)
    for key in displaced:
        origin = positions[key]
        candidates = vacated or {
            (column, row)
            for column in range(columns)
            for row in range(rows)
            if (column, row) not in occupied
        }
        # A valid layout always has enough vacancies, including on a full grid.
        # Keep the original snapshot if an inconsistent caller violates that.
        if not candidates:
            return positions
        cell = min(candidates, key=lambda candidate: (abs(candidate[0] - origin[0]) + abs(candidate[1] - origin[1]), *candidate))
        result[key] = cell
        occupied.add(cell)
        vacated.discard(cell)
    return result


def rectangle_hits(
    rects: dict[str, tuple[float, float, float, float]],
    rectangle: tuple[float, float, float, float],
) -> set[str]:
    """Return keys with positive-area overlap, including backwards drag boxes.

    Rectangles use (x, y, width, height). Negative sizes are normalized for both
    the drag rectangle and icon bounds. A zero-width/height rectangle or mere
    edge/corner contact never selects an icon.
    """
    def bounds(rect):
        x, y, width, height = rect
        return min(x, x + width), min(y, y + height), max(x, x + width), max(y, y + height)

    left, top, right, bottom = bounds(rectangle)
    if left >= right or top >= bottom:
        return set()
    hits = set()
    for key, rect in rects.items():
        icon_left, icon_top, icon_right, icon_bottom = bounds(rect)
        if max(left, icon_left) < min(right, icon_right) and max(top, icon_top) < min(bottom, icon_bottom):
            hits.add(key)
    return hits
