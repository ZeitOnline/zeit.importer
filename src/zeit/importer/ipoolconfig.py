from lxml import etree


class IPoolConfig(object):

    def __init__(self, ressource):
        self.products = {}
        self.product_map = {}
        self.ressource = ressource
        self.ressort_map = {}
        self.parse_config()

    def parse_config(self):
        self.tree = etree.fromstring(self.ressource.data.read())
        products = self.tree.xpath('/config/product')
        if products:
            for p in products:
                k4_id = p.findtext('k4id')
                label = p.findtext('label')
                id = p.get('id')
                if k4_id:
                    self.products[id] = label
                    self.product_map[k4_id] = id

                for ressort in p.xpath('ressort'):
                    self.ressort_map[(
                        k4_id, ressort.get('name'))] = ressort.get('id')
