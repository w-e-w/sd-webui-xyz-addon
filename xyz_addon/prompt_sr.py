from .utils import no_type_cast, TrueTrue, csv_string_to_list_strip
import itertools


def prepare_sr_placeholder(vals):
    valslist = csv_string_to_list_strip(vals)
    placeholder = valslist[0]
    return list(map(lambda v: (placeholder, v), valslist[1:]))


def combinatorics(vals, function):
    placeholder, *replacement_list = csv_string_to_list_strip(vals)
    placeholder, _, length = placeholder.partition(':')
    r1, r2 = None, None
    if length := length.strip():
        r1, _, r2 = length.partition('-')
        if r2 := r2.strip():
            r2 = int(r2)
        r1 = int(r1.strip())
    if not r1:
        r1, r2 = 1, len(replacement_list)
    if not r2:
        r2 = r1
    r1, r2 = (r2, r1) if r1 > r2 else (r1, r2)
    return [item for r in range(r1, r2 + 1) for item in map(lambda c: (placeholder, ', '.join(c)), function(replacement_list, r))]


def combinations(s):
    return combinatorics(s, itertools.combinations)


def permutations(s):
    return combinatorics(s, itertools.permutations)


def create_axes(xyz_grid):
    class PromptSR(xyz_grid.AxisOption):
        def __init__(self, label, prepare):
            self.label = label
            self.type = no_type_cast
            self.confirm = None
            self.cost = 0.0
            self.prepare = prepare
            self.choices = None
            self.is_img2img = TrueTrue()

        def apply(self, p, x, xs):
            """Similar functionality to the built-in Prompt S/R, but the first item will be replaced with <blank>"""
            placeholder, replacement = x
            if placeholder not in p.prompt and placeholder not in p.negative_prompt:
                raise RuntimeError(f'{self.label}: {placeholder}" was not found in prompt or negative prompt.')
            p.prompt, p.negative_prompt = p.prompt.replace(placeholder, replacement), p.negative_prompt.replace(placeholder, replacement)

        @staticmethod
        def prepare(vals):
            valslist = xyz_grid.csv_string_to_list_strip(vals)
            placeholder = valslist[0]
            return list(map(lambda v: (placeholder, v), valslist[1:]))

        def format_value(self, p, opt, x):
            return str(x[1])

    return [
        PromptSR(label='[Addon] Prompt S/R Placeholder', prepare=prepare_sr_placeholder),
        PromptSR(label='[Addon] Prompt S/R Combinations', prepare=combinations),
        PromptSR(label='[Addon] Prompt S/R Permutations', prepare=permutations),
    ]
