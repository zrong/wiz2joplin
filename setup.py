from pathlib import Path
import re
from setuptools import setup, find_packages

here = Path(__file__).parent

def read(*parts):
    """ 读取一个文件并返回内容
    """
    return here.joinpath(*parts).read_text(encoding='utf8')

def find_version(*file_paths):
    """ 从 __init__.py 的 __version__ 变量中提取版本号
    """
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")

def find_requires(*file_paths):
    """ 将提供的 requirements.txt 按行转换成 list
    """
    require_file = read(*file_paths)
    return require_file.splitlines()

def static_requires():
    return ['idna==2.10', 'chardet', 'httpx', 'inscriptis']

classifiers = [
    'Programming Language :: Python :: 3.9',
    'Development Status :: 4 - Beta',
    'Environment :: Console',
    'Topic :: System :: Shells',
    'Topic :: Utilities',
    'Topic :: Text Processing :: Markup :: HTML',
    'Topic :: Text Processing :: Markup :: Markdown',
    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
]

# 使用 flask 的扩展
entry_points = {
    'console_scripts': [
        'w2j=w2j:main'
    ]
}

package_data = {
    '': ['requirements.txt']
}


setup(
    python_requires='>=3.9, <4',
    name = "w2j",
    version=find_version('w2j', '__init__.py'),
    author = "zrong",
    author_email = "zrongzrong@gmail.com",
    url = "https://github.com/zrong/wiz2joplin",
    description = "A tool for migrating from WizNote to Joplin.",
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    license = "GPLv3",
    keywords = "development zrong wiznote joplin",
    packages = find_packages(exclude=['test*', 'output', 'venv']),
    install_requires=static_requires(),
    entry_points=entry_points,
    include_package_data = True,
    zip_safe=False,
    classifiers = classifiers, 
    package_data=package_data
)
