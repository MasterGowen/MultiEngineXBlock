"""Setup for multiengine XBlock."""

import os
import re
import glob
import shutil
from setuptools import setup, find_packages
from setuptools.command.build_py import build_py
import subprocess


class CustomBuildPy(build_py):
    """Кастомная команда сборки для работы с git-подмодулями."""
    
    def run(self):
        """Запуск кастомной логики перед стандартной сборкой."""
        if os.path.exists(".git"):
            # Проверяем наличие git в системе
            if not shutil.which("git"):
                self.announce(
                    "Git не найден в PATH. Пропускаем обновление подмодулей",
                    level=2
                )
            else:
                try:
                    subprocess.check_call(
                        ["git", "submodule", "update", "--init", "--recursive"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except subprocess.CalledProcessError as e:
                    self.warn(f"Ошибка при обновлении подмодулей: {e}")
        super().run()


def package_data(pkg, roots):
    """Улучшенный поиск статических данных пакета.
    
    Использует рекурсивные шаблоны вместо os.walk для корректной работы
    с глубокой вложенностью файлов.
    """
    data = []
    for root in roots:
        # Для рекурсивного поиска используем **/* шаблон
        pattern = os.path.join(pkg, root)
        if "**" in root:
            # Уже рекурсивный шаблон
            for path in glob.glob(pattern, recursive=True):
                if os.path.isfile(path):
                    data.append(os.path.relpath(path, pkg))
        else:
            # Добавляем рекурсивный поиск
            recursive_pattern = os.path.join(pkg, root, "**/*")
            for path in glob.glob(recursive_pattern, recursive=True):
                if os.path.isfile(path):
                    data.append(os.path.relpath(path, pkg))
            # Также добавляем файлы в корневой директории
            root_pattern = os.path.join(pkg, root, "*")
            for path in glob.glob(root_pattern):
                if os.path.isfile(path):
                    data.append(os.path.relpath(path, pkg))
    
    return {pkg: data}


setup(
    name="multiengine-xblock",
    version="0.3.0",
    description="multiengine XBlock",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/MasterGowen/MultiEngineXBlock",
    author="UrFU.Online",
    license="AGPL-3.0-or-later",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Framework :: XBlock",
    ],
    packages=find_packages(),
    cmdclass={"build_py": CustomBuildPy},
    include_package_data=True,
    install_requires=[
        "XBlock",
    ],
    entry_points={
        "xblock.v1": [
            "multiengine = multiengine:MultiEngineXBlock",
        ]
    },
    package_data=package_data("multiengine", ["static", "public", "scenarios/**/*"])
)