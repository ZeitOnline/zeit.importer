from setuptools import setup, find_packages

setup(
    name='zeit.importer',
    version='0.1dev',
    author='Martin Borho',
    author_email='martin@borho.net',
    url='http://trac.gocept.com/zeit',
    description="""\
""",
    packages=find_packages('src'),
    package_dir = {'': 'src'},
    include_package_data = True,
    zip_safe=False,
    license='gocept proprietary',
    namespace_packages = ['zeit'],
    install_requires=[
        'zeit.connector',
        'setuptools',
        'pytz',
        ],
    entry_points = """
        [console_scripts]  
        k4import = zeit.importer.k4import:main
        """
)
