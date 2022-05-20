from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name="silver_flutterwave",
    version="2.2.2",
    description="Stripe pay",
    long_description="Stripe Payment in Olitt",
    url="",
    author="Idah",
    packages=["silver_flutterwave"],
    include_package_data=True,
    package_data={
        #  "templates": ["templates/*.html"],
    }
    # package_dir={"": "src"},
    # packages=find_packages(where="src"),
)
