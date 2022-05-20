from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name="silver_flutterwave",
    version="2.2.8",
    description="Stripe pay",
    long_description="Stripe Payment in Olitt",
    url="",
    author="Idah",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "templatetags": ["*.py"],
        "migrations": ["*.py"],
        "silver_flutterwave": ["silver_flutterwave/*.html"],
    }
    # package_dir={"": "src"},
    # packages=find_packages(where="src"),
)
