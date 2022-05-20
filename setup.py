from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name="silver_flutterwave",
    version="2.1.0",
    description="Stripe pay",
    long_description="Stripe Payment in Olitt",
    url="",
    author="Idah",
    package_data = {
    'templates': ['*'],
    'templatetags:['*'],
    'migrations:['*']
}
    # package_dir={"": "src"},
    # packages=find_packages(where="src"),
    packages=["silver_flutterwave"],
)
