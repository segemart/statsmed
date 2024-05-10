from setuptools import setup, find_packages


setup(name='statsmed',
        version='0.0.2',
        description='Statistics with Figures for medical data analysis',
        url='https://github.com/segemart/statsmed',
        author='Martin Segeroth',
        python_requires='>=3.8.8',
        license='Apache 2.0',
        packages=find_packages(),
        install_requires=[
            'numpy',
            'scipy>=1.10.1',
            'matplotlib>=3.6.2'
        ],
        zip_safe=False,
        classifiers=[
            'Intended Audience :: Science/Research',
            'Programming Language :: Python',
            'Topic :: Scientific/Engineering',
            'Operating System :: Unix',
            'Operating System :: MacOS'
        ]
    )
