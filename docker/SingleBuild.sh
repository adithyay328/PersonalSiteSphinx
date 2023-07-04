# Runs a single sphinx build,
# instead of starting the autorun
# from the DockerRun.sh
# script.
docker pull adithyay328/sphinx_site_template
docker run --mount type=bind,source="$(cd ../ && pwd)",target=/app adithyay328/sphinx_site_template bash -c 'cd /app/site; sphinx-build -b html source build'