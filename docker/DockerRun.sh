# A bash script that runs the entire build process
# directly in docker. Only use if you are on linux
# or otherwise have docker installed locally.
docker pull adithyay328/sphinx_site_template
docker run -d --mount type=bind,source="$(cd ../ && pwd)",target=/app adithyay328/sphinx_site_template