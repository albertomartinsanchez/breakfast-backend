@echo off
echo Installing test dependencies...
pip install -r requirements-dev.txt

echo.
echo Running tests with coverage...
python -m pytest

echo.
echo Coverage report: htmlcov/index.html
pause