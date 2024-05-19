from .utils import TrueTrue, no_type_cast, csv_string_to_list_strip
import itertools


def prepare_sr(vals, include_first=False):
    valslist = csv_string_to_list_strip(vals)
    placeholder = valslist[0]
    return list(map(lambda v: (placeholder, v), valslist[0 if include_first else 1:]))


def combinatorics(vals, function, include_first=False):
    placeholder, *replacement_list = csv_string_to_list_strip(vals)
    *length, placeholder = csv_string_to_list_strip(placeholder, ':', "'")
    replacement_list = [placeholder] + replacement_list if include_first else replacement_list
    match len(length):
        case 0:
            r1, r2 = 1, len(replacement_list)
        case 1:
            r1 = r2 = int(length[0])
        case _:
            r1, r2 = int(length[0]), int(length[1])
    r1, r2 = (r2, r1) if r1 > r2 else (r1, r2)
    r1, r2 = 0 if r1 < 0 else r1, len(replacement_list) if r2 > len(replacement_list) else r2
    return [item for r in range(r1, r2 + 1) for item in map(lambda c: (placeholder, ', '.join(c)), function(replacement_list, r))]


def create_axes(xyz_grid):
    class PromptSR(xyz_grid.AxisOption):
        def __init__(self, label, include_first, mode=None):
            self.label = label
            self.type = no_type_cast
            self.confirm = None
            self.cost = 0.0
            self.choices = None
            self.is_img2img = TrueTrue()
            self.include_first = include_first
            self.mode = mode

        def apply(self, p, x, xs):
            """Similar functionality to the built-in Prompt S/R, but the first item will be replaced with <blank>"""
            placeholder, replacement = x
            if placeholder not in p.prompt and placeholder not in p.negative_prompt:
                raise RuntimeError(f'{self.label}: {placeholder}" was not found in prompt or negative prompt.')
            p.prompt, p.negative_prompt = p.prompt.replace(placeholder, replacement), p.negative_prompt.replace(placeholder, replacement)

        def prepare(self, vals):
            match self.mode:
                case 'c':
                    return combinatorics(vals, itertools.combinations, self.include_first)
                case 'p':
                    return combinatorics(vals, itertools.permutations, self.include_first)
                case _:
                    return prepare_sr(vals, self.include_first)

        @staticmethod
        def format_value(p, opt, x):
            return str(x[1])

    return [
        PromptSR('[Addon] Prompt S/R', True),
        PromptSR('[Addon] Prompt S/R (P)', False),
        PromptSR('[Addon] Prompt S/R Combinations', True, 'c'),
        PromptSR('[Addon] Prompt S/R Combinations (P)', False, 'c'),
        PromptSR('[Addon] Prompt S/R Permutations', True, 'p'),
        PromptSR('[Addon] Prompt S/R Permutations (P)', False, 'p'),
    ]
