from __future__ import annotations

from lineage.structural import control_events, python_ast_streams
from lineage.transforms import rename_user_identifiers

_PYTHON = '''
def total(xs, scale):
    amount = 0
    for item in xs:
        if item > scale:
            amount += item
        else:
            amount -= item
    return amount
'''

_JAVASCRIPT = '''
function total(xs, scale) {
  let amount = 0;
  for (const item of xs) {
    if (item > scale) {
      amount += item;
    } else {
      amount -= item;
    }
  }
  return amount;
}
'''


def _labels(source: str, language: str) -> list[str]:
    return [label for label, _line in control_events(source, f"mod.{language[:2]}", language, 0)]


def test_python_ast_shape_ignores_renames() -> None:
    renamed = rename_user_identifiers(_PYTHON)
    left = python_ast_streams(_PYTHON, 0)
    right = python_ast_streams(renamed, 0)
    assert left
    assert [labels for labels, _lines in left] == [labels for labels, _lines in right]


def test_python_and_javascript_control_shapes_align() -> None:
    assert _labels(_PYTHON, "python") == _labels(_JAVASCRIPT, "javascript")


def test_an_extra_branch_changes_the_ast_shape() -> None:
    changed = _PYTHON.replace("amount -= item", "amount -= item\n            amount = 0")
    left = python_ast_streams(_PYTHON, 0)[0][0]
    right = python_ast_streams(changed, 0)[0][0]
    assert left != right
