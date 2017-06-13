from PIL import Image
from zeit.importer.highres import ImageHash
import io
import zeit.importer.testing


class HighresTest(zeit.importer.testing.TestCase):

    def test_imagehash_initializes_with_settings(self):
        fp = io.BytesIO()
        Image.new('1', (1, 1)).save(fp, 'jpeg')
        hash_ = ImageHash('foobar', fp)
        self.assertEquals(hash_.size, self.settings['highres_sample_size'])
        self.assertEquals(hash_.cutoff, self.settings['highres_diff_cutoff'])
        self.assertEquals(hash_.id, 'foobar')

    def test_imagehash_calculates_plausible_hash_values(self):
        fp = io.BytesIO()
        image = Image.new('L', (2, 2))
        image.putdata([250, 15, 140, 190])
        image = image.resize((4, 4))
        image.save(fp, 'jpeg')
        hash_ = ImageHash('', fp)
        self.assertEquals(hash_['average_hash'], 'CC77')
        self.assertEquals(hash_['dhash'], '05C1')
        self.assertEquals(hash_['dhash_vertical'], '083A')

    def test_imagehash_finds_plausible_matches(self):
        hashes = []
        for id_, pixels in enumerate((
                [15, 255, 255, 15],
                [250, 70, 80, 245],
                [10, 240, 240, 10],
                [70, 70, 80, 75],
                [0, 0, 250, 255])):
            fp = io.BytesIO()
            image = Image.new('L', (2, 2))
            image.putdata(pixels)
            image = image.resize([self.settings['highres_sample_size']] * 2)
            image.save(fp, 'jpeg')
            hash_ = ImageHash(id_, fp)
            hashes.append(hash_)
        master = hashes.pop(0)
        match = master.find_match(hashes)
        self.assertEquals(match.id, 2)
