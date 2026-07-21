from setuptools import setup, find_packages
import money_recovery

setup(
    name="money_recovery",
    version=money_recovery.__version__,
    description="Delayed Payment / Receivables Recovery Tooling for ERPNext",
    author="Bizaxl",
    author_email="support@bizaxl.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[],
)
