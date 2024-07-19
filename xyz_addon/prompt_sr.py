from .utils import TrueTrue, no_type_cast, csv_string_to_list_strip
from modules import patches, script_callbacks
from functools import wraps
import itertools


def prepare_sr(vals, include_first=False):
    valslist = csv_string_to_list_strip(vals)
    placeholder = valslist[0]
    return list(map(lambda v: (placeholder, v[1], v[0]), enumerate(valslist[0 if include_first else 1:])))


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
    return [item for r in enumerate(range(r1, r2 + 1)) for item in map(lambda c: (placeholder, ', '.join(c[1]), (c[0], r[0])), enumerate(function(replacement_list, r[1])))]


def wrap_process_images(func):
    @wraps(func)
    def wrapper(p, *args, **kwargs):
        res = func(p, *args, **kwargs)
        if (prompt := getattr(p, 'xyz_addon_placeholder_original_prompt', None)) and p.all_prompts:
            p.all_prompts[0] = prompt
        if (negative_prompt := getattr(p, 'xyz_addon_placeholder_original_negative_prompt', None)) and p.all_negative_prompts:
            p.all_negative_prompts[0] = negative_prompt
        return res
    return wrapper


def create_axes(xyz_grid):
    patches.patch(__name__, xyz_grid, 'process_images', wrap_process_images(xyz_grid.process_images))
    script_callbacks.on_script_unloaded(lambda: patches.undo(__name__, xyz_grid, 'process_images'))  # in this case, undo should not be necessary

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
            placeholder, replacement, index = x
            if not self.include_first and index == 0:
                if getattr(p, 'xyz_addon_placeholder_original_prompt', None) is None:
                    p.xyz_addon_placeholder_original_prompt = p.prompt
                if getattr(p, 'xyz_addon_placeholder_original_negative_prompt', None) is None:
                    p.xyz_addon_placeholder_original_negative_prompt = p.negative_prompt

            p.xyz_addon_placeholder = not self.include_first

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
