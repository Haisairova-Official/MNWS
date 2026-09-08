"""Display-independent tests for rubber-band selection and group dragging."""

from __future__ import annotations

from copy import deepcopy
import itertools
import unittest

from desktop_layer.selection import move_group, rectangle_hits


class GroupMovementTests(unittest.TestCase):
    def test_move_into_empty_space_preserves_shape_and_input(self):
        layout = {"a": [0, 0], "b": [0, 2], "c": [1, 1], "stay": [4, 0]}
        original = deepcopy(layout)
        self.assertEqual(
            move_group(layout, {"a", "b", "c"}, 2, 1, 5, 5),
            {"a": (2, 1), "b": (2, 3), "c": (3, 2), "stay": (4, 0)},
        )
        self.assertEqual(layout, original)

    def test_clamp_whole_group_at_each_edge(self):
        layout = {"a": (1, 1), "b": (2, 3)}
        self.assertEqual(move_group(layout, set(layout), -10, -20, 5, 6), {"a": (0, 0), "b": (1, 2)})
        self.assertEqual(move_group(layout, set(layout), 10, 20, 5, 6), {"a": (3, 3), "b": (4, 5)})

    def test_single_icon_swaps_with_destination_occupant(self):
        layout = {"a": (0, 0), "b": (1, 1), "c": (1, 0)}
        self.assertEqual(move_group(layout, {"a"}, 1, 1, 2, 2), {"a": (1, 1), "b": (0, 0), "c": (1, 0)})

    def test_contiguous_group_can_overlap_its_old_cells_on_full_grid(self):
        layout = {"a": (0, 0), "b": (1, 0), "c": (2, 0), "d": (3, 0)}
        self.assertEqual(move_group(layout, {"a", "b"}, 1, 0, 4, 1), {"a": (1, 0), "b": (2, 0), "c": (0, 0), "d": (3, 0)})

    def test_scattered_group_displaces_into_nearest_vacated_cells(self):
        layout = {"a": (0, 0), "b": (0, 2), "c": (1, 0), "d": (1, 2), "stay": (2, 1)}
        self.assertEqual(
            move_group(layout, {"a", "b"}, 1, 0, 3, 3),
            {"a": (1, 0), "b": (1, 2), "c": (0, 0), "d": (0, 2), "stay": (2, 1)},
        )

    def test_vacated_cells_are_preferred_over_nearer_preexisting_holes(self):
        layout = {"a": (0, 0), "b": (4, 0)}
        self.assertEqual(move_group(layout, {"a"}, 4, 0, 5, 2), {"a": (4, 0), "b": (0, 0)})

    def test_displacement_is_independent_of_dictionary_and_selection_order(self):
        layout = {"a": (0, 1), "b": (1, 0), "c": (1, 2), "d": (2, 1)}
        expected = {"a": (1, 2), "b": (2, 1), "c": (0, 1), "d": (1, 0)}
        for ordering in itertools.permutations(layout):
            shuffled = {key: layout[key] for key in ordering}
            self.assertEqual(move_group(shuffled, {"b", "a"}, 1, 1, 3, 3), expected)

    def test_empty_unknown_selection_and_zero_or_clamped_movement_are_noops(self):
        layout = {"a": (0, 0), "b": (1, 1)}
        for selected, dx, dy in [(set(), 1, 1), ({"missing"}, 1, 1), ({"a"}, 0, 0), ({"a"}, -100, -100), (set(layout), 100, -100)]:
            with self.subTest(selected=selected, dx=dx, dy=dy):
                self.assertEqual(move_group(layout, selected, dx, dy, 2, 2), layout)
        self.assertEqual(move_group({}, {"missing"}, 1, 1, 2, 2), {})
        self.assertEqual(move_group(layout, {"a", "missing"}, 1, 0, 2, 2), {"a": (1, 0), "b": (1, 1)})

    def test_invalid_dimensions_and_deltas_do_not_drop_entries(self):
        layout = {"a": (0, 0)}
        for columns, rows in [(0, 2), (2, 0), (-1, 2), (2, -1), (None, 2), (2, "3"), (True, 2), (2.5, 2)]:
            with self.subTest(columns=columns, rows=rows):
                self.assertEqual(move_group(layout, {"a"}, 1, 1, columns, rows), layout)
        for dx, dy in [(None, 1), (1, "2"), (1.5, 1), (True, 1)]:
            self.assertEqual(move_group(layout, {"a"}, dx, dy, 3, 3), layout)

    def test_invalid_grid_input_is_preserved_without_partial_repair(self):
        for layout in [{"a": (0, 0), "b": (0, 0)}, {"a": (10, 0)}, {"a": (True, 0)}, {"a": (0,)}, {"a": (-1, 0)}]:
            self.assertEqual(move_group(layout, {"a"}, 1, 1, 3, 3), layout)

    def test_all_small_grid_layouts_preserve_keys_bounds_shape_and_other_entries(self):
        # Exhaust all partial/full 2x2 layouts, selections, and drag directions.
        # This exercises overlapping source/destination sets and edge clamping.
        cells = list(itertools.product(range(2), repeat=2))
        for size in range(1, 5):
            for used in itertools.combinations(cells, size):
                layout = {str(index): cell for index, cell in enumerate(used)}
                for selected_size in range(size + 1):
                    for chosen in itertools.combinations(layout, selected_size):
                        selected = set(chosen)
                        for dx, dy in itertools.product((-5, -1, 0, 1, 5), repeat=2):
                            moved = move_group(layout, selected, dx, dy, 2, 2)
                            self.assertEqual(set(moved), set(layout))
                            self.assertEqual(len(set(moved.values())), size)
                            self.assertTrue(all(cell in cells for cell in moved.values()))
                            if selected:
                                shifts = {(moved[key][0] - layout[key][0], moved[key][1] - layout[key][1]) for key in selected}
                                self.assertEqual(len(shifts), 1)
                                destinations = {moved[key] for key in selected}
                                for key in set(layout) - selected:
                                    if layout[key] not in destinations:
                                        self.assertEqual(moved[key], layout[key])


class RectangleSelectionTests(unittest.TestCase):
    def test_selects_positive_overlap_but_not_edge_contact(self):
        rects = {"inside": (2, 2, 3, 3), "cross": (9, 9, 5, 5), "edge": (10, 0, 5, 5), "corner": (10, 10, 1, 1), "outside": (-9, -9, 2, 2)}
        self.assertEqual(rectangle_hits(rects, (0, 0, 10, 10)), {"inside", "cross"})

    def test_all_drag_directions_have_identical_hits(self):
        rects = {"a": (1, 1, 3, 3), "b": (8, 8, -2, -2), "c": (20, 20, 2, 2)}
        for rectangle in [(0, 0, 10, 10), (10, 0, -10, 10), (0, 10, 10, -10), (10, 10, -10, -10)]:
            self.assertEqual(rectangle_hits(rects, rectangle), {"a", "b"})

    def test_zero_area_rectangles_never_hit(self):
        rects = {"a": (1, 1, 0, 10), "b": (1, 1, 10, 0), "c": (1, 1, 1, 1)}
        self.assertEqual(rectangle_hits(rects, (0, 0, 10, 10)), {"c"})
        self.assertEqual(rectangle_hits(rects, (1, 1, 0, 10)), set())
        self.assertEqual(rectangle_hits(rects, (1, 1, 10, 0)), set())
        self.assertEqual(rectangle_hits({}, (0, 0, 10, 10)), set())

    def test_fractional_and_negative_coordinates(self):
        rects = {"a": (-1.5, -1.5, 1, 1), "b": (-0.5, -0.5, 0.5, 0.5), "edge": (0, 0, 1, 1)}
        self.assertEqual(rectangle_hits(rects, (-1, -1, 1, 1)), {"a", "b"})


if __name__ == "__main__":
    unittest.main()
