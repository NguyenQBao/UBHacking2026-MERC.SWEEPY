"""Copy a melody list [(hz, seconds), ...] from a Python file into sounds.json.

Example (rover controller.py keeps its melody in a variable named `melody`):
    python3 melody_from_python.py ../UBHacking2026/controller.py melody rover_song
The file is parsed, never executed. Restart run.py to get a new button.
"""
import argparse
import ast
import json
from pathlib import Path
from control import load_sounds

HERE = Path(__file__).resolve().parent


def find_list(source, variable):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == variable for t in node.targets):
            return [list(note) for note in ast.literal_eval(node.value)]
    raise ValueError(f'No list assigned to {variable!r}')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('source', help='Python file containing the melody list')
    p.add_argument('variable', help='Variable name, e.g. melody or HPBD')
    p.add_argument('name', help='Sound name for the button (a-z, 0-9, _)')
    p.add_argument('--out', default=str(HERE/'sounds.json'))
    args = p.parse_args()
    notes = find_list(Path(args.source).read_text(encoding='utf-8'), args.variable)
    out = Path(args.out)
    data = json.loads(out.read_text()) if out.is_file() else {}
    data[args.name] = notes
    tmp = out.with_suffix('.tmp')
    tmp.write_text(json.dumps(data))
    load_sounds(tmp)  # validate before replacing
    tmp.replace(out)
    print(f'{args.name}: {len(notes)} notes, {sum(n[1] for n in notes):.1f} s -> {out}')


if __name__ == '__main__':
    main()
