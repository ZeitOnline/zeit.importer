from setuptools import setup, find_packages


setup(
    name='zeit.importer',
    version='1.4.7.dev0',
    author='Martin Borho, gocept, Zeit Online',
    author_email='zon-backend@zeit.de',
    url='http://www.zeit.de/',
    description=" Convert print XML to vivi format (Phase 1/2)",
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    license='BSD',
    namespace_packages=['zeit'],
    install_requires=[
        'Pillow',
        'pytz',
        'setuptools',
        'zeit.connector',
        'zope.component',
        'zope.interface',
    ],
    entry_points="""
        [console_scripts]
        k4import=zeit.importer.k4import:main
        """
)
