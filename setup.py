from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name="silver_flutterwave",
    version="2.3.6",
    description="Stripe pay",
    long_description="Stripe Payment in Olitt",
    url="",
    author="Idah",
    packages=find_packages(),
    include_package_data=True,
    package_data={
       "templatetags": ['*.py'],
       "migrations":['*.py'],

        
    }

)
