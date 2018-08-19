from setuptools import setup

setup(
    name='odbcnotebook',
    packages=['odbcnotebook'],
    entry_points = {
        'console_scripts':
        ['odbc-server = odbcnotebook.server:main']
    },
    author='Chris Marchetti',
    version='0.1',
    description='An ODBC backend for the ADONotebook protocol',
    author_email='adamnew123456@gmail.com',
    keywords=['networking', 'databases'],
    install_requires=['pyodbc'],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: BSD License',
        'Development Status :: 3 - Alpha',
        'Topic :: Database :: Frontends',
        'Topic :: Utilities'
    ])
