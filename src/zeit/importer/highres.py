import math
import zeit.importer.interfaces
import zope.component

from PIL import Image


Image.MAX_IMAGE_PIXELS = 10 ** 8  # Let's not bother with 100+ MP images
Image.warnings.simplefilter('error', Image.DecompressionBombWarning)


class ImageHash(dict):
    """Image hash class that partially reimplements hash functions from
    the library ImageHash without the use of numpy or scipy.

    This way, our highres matcher is a lot easier to deploy with batou,
    while still working well and fast enough for our purposes.
    """

    HASH_FUNCTIONS = ('average_hash', 'dhash', 'dhash_vertical')

    def __init__(self, id_, fp):
        settings = zope.component.getUtility(
            zeit.importer.interfaces.ISettings)
        self.size = settings.get('highres_sample_size', 8)
        self.cutoff = settings.get('highres_diff_cutoff', 0.25)
        self.id = id_
        format = '0%sx' % int(math.ceil(self.size ** 2 / 4.0))
        dim = (self.size, self.size)
        image = Image.open(fp).convert('L').resize(dim, Image.ANTIALIAS)
        for func in self.HASH_FUNCTIONS:
            bits = getattr(self, func)(image)
            self[func] = int(''.join(bits), 2).__format__(format).upper()

    def __sub__(self, other):
        differences = []
        for func in self.HASH_FUNCTIONS:
            diff = sum(c1 != c2 for c1, c2 in zip(self[func], other[func]))
            differences.append(float(diff))
        return sum(differences) / len(self)

    def __repr__(self):
        return object.__repr__(self)

    def find_match(self, images):
        matches = [(self - i, i) for i in images]
        max_diff = max(d for d, i in matches)
        if max_diff:
            matches = [(d / max_diff, i) for d, i in matches]
        diff, match = min(matches, key=lambda i: i[0])
        if diff < self.cutoff:
            return match

    @staticmethod
    def average_hash(image):
        pixels = list(image.getdata())
        average = float(sum(pixels)) / len(pixels)
        return ['1' if p > average else '0' for p in pixels]

    @staticmethod
    def dhash(image):
        size = min(image.size)
        pixels = list(image.getdata())
        rows = [pixels[r * size: r * size + size] for r in range(size)]
        adjacent = [a for r in (zip(r[:-1], r[1:]) for r in rows) for a in r]
        return ['1' if p1 > p2 else '0' for p1, p2 in adjacent]

    @staticmethod
    def dhash_vertical(image):
        return ImageHash.dhash(image.rotate(90))
